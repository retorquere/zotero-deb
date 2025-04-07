#!/usr/bin/env crystal

require "http/client"
require "json"
require "uri"
require "path"
require "yaml"
require "ini"
require "process"

def chdir(path : String | Path, &block)
  back = Dir.current
  Dir.cd(path.to_s) do
    yield
  end
  Dir.cd(back)
end

def download(url : String, filename : String) : String
  cmd = "curl #{Process.quote([ "-sLf", "-o", filename, url ])}"
  print cmd
  system "#{cmd} || true"
  puts File.file?(filename) ? " : succeeded" : " : failed"
  return filename
end

def run(cmd : String, args : Array(String) = [] of String)
  cmd = "#{cmd} #{Process.quote(args)}".strip
  puts cmd
  return if system cmd
  Process.exit(1)
end

class Config
  include YAML::Serializable

  class Maintainer
    include YAML::Serializable

    property name : String
    property email : String
    property gpgkey : String
  end

  class Common
    include YAML::Serializable

    property dependencies : Array(String)
  end

  class Client
    include YAML::Serializable

    property description : String = ""
    property dependencies : Array(String) = [] of String
    property release : Hash(String, Int32) = Hash(String, Int32).new

    @[YAML::Field(ignore: true)]
    property section : String = ""

    def version(v)
      v += "-#{@release[v]}" if @release.has_key?(v)
      return v
    end
  end

  property maintainer : Maintainer
  property common : Common
  property zotero : Client
  property zotero6 : Client
  @[YAML::Field(key: "zotero-beta")]
  property zotero_beta : Client

  property staging : String

  @[YAML::Field(ignore: true)]
  property package : String = ""
  @[YAML::Field(ignore: true)]
  property version : String = ""

  def self.load
    loaded = self.from_yaml(File.read("config.yml"))
    loaded.staging = "#{Path.new(loaded.staging).expand}"
    loaded.zotero.dependencies += loaded.common.dependencies
    loaded.zotero6.dependencies += loaded.common.dependencies
    loaded.zotero_beta.dependencies += loaded.common.dependencies
    return loaded
  end

  def client : Client
    return case @package
      when "zotero"
        @zotero
      when "zotero-beta"
        @zotero_beta
      when "zotero6"
        @zotero6
      else
        raise "Unkown package #{@package}"
    end
  end
end

class Zotero
  property version : String
  property release : Int32
  property url : String

  property arch : String
  property beta : Bool = false
  property legacy : Bool = false
  property name : String = "Zotero"
  property bin : String

  property config : Config

  property vendor : String = ""
  property license : String = ""
  property homepage : String = ""

  def initialize(@arch : String, mode : String)
    case mode
      when "beta"
        @beta = true
      when "legacy"
        @legacy = true
      when "release"
        # pass
      else
        raise "unknown mode #{mode}"
    end

    arch = case @arch
      when "amd64"
        "x86_64"
      when "i386"
        "i686"
      else
        raise "unknown architecture #{arch}"
    end

    @config = Config.load

    @bin = "zotero"

    @vendor = "Zotero"
    @licence = "GNU Affero General Public License (version 3)"
    @homepage = "https://www.zotero.org/"

    response = HTTP::Client.get("https://www.zotero.org/download/client/manifests/#{ @beta ? "beta" : "release" }/updates-linux-#{arch}.json")
    raise "Could not get Zotero version" unless response.success?
    versions = JSON.parse(response.body).as_a.map{|v| v["version"].as_s}
    if @legacy
      versions = versions.select{|v| v.starts_with? "6" }
      versions << "6.0.35" # assure at least one version remains available
      @config.package = "zotero6"
    elsif @beta
      @config.package = "zotero-beta"
    else
      @config.package = "zotero"
    end
    vtuple = ->(v : String) { v.split(/[-.]/).map{|part| part =~ /^\d+$/ ? part.to_i : 0 } }
    versions = versions.sort{|v1, v2| vtuple.call(v1) <=> vtuple.call(v2) }
    @version = versions[-1]
    print @version, " from ", versions
    puts
    @url = "https://download.zotero.org/client/release/#{@version}/Zotero-#{@version}_linux-#{arch}.tar.bz2"

    @release = @config.client.release.fetch(@version, 0)
  end

  def mkdir(d)
    d = "#{d}"
    d = "#{Path[@config.staging, d]}" unless d.starts_with?("/")
    run "mkdir", ["-p", d]
    return d
  end

  def stage
    run "rm", ["-rf", @config.staging]

    staging = self.mkdir(@config.staging)
    tarball = File.tempfile("#{@config.package}.tar.bz2").path
    download @url, tarball
    run "tar", ["-xjf", tarball, "-C", staging, "--strip-components=1"]

    # enable mozilla.cfg
    File.open(Path[self.mkdir(Path[staging, "defaults", "pref"]), "local_settings.js"], "a") do |f|
      f.puts "" if f.size == 0 # add empty line as separator
      f.puts "pref(\"general.config.obscure_value\", 0); // only needed if you do not want to obscure the content with ROT-13"
      f.puts "pref(\"general.config.filename\", \"mozilla.cfg\");"
    end

    # disable auto-update
    File.open(Path[staging, "mozilla.cfg"], "a") do |f|
      # this file needs to start with '//' -- if it's empty, add it, if not, it should already be there
      f.puts (f.size == 0 ? "//" : "")
      # does not make it impossible for the user to request an update (which will fail, because this install is root-owned), but Zotero won't ask the user to do so
      f.puts "lockPref(\"app.update.enabled\", false);"
      f.puts "lockPref(\"app.update.auto\", false);"
    end

    desktop = INI.parse(File.read("#{Path[staging, "#{@bin}.desktop"]}"))
    @config.client.section = desktop["Desktop Entry"].fetch("Categories", "Science;Office;Education;Literature").rstrip(";")
    desktop["Desktop Entry"]["Exec"] = "/usr/lib/#{@config.package}/#{@bin} #{@beta || @legacy ? "--class #{@config.package}" : ""} --url %u"

    desktop["Desktop Entry"]["Name"] = @name
    desktop["Desktop Entry"]["Name"] += " Beta" if @beta
    desktop["Desktop Entry"]["Name"] += " (Legacy)" if @legacy

    desktop["Desktop Entry"]["Comment"] = "#{@name} is a free, easy-to-use tool to help you collect, organize, cite, and share research"
    desktop["Desktop Entry"]["Icon"] = "#{Path["/usr/lib", @config.package, @legacy ? "chrome/icons/default/default256.png" : "icons/icon128.png"]}"
    desktop["Desktop Entry"]["MimeType"] = [
      "x-scheme-handler/zotero",
      "application/x-endnote-refer",
      "application/x-research-info-systems",
      "text/ris",
      "text/x-research-info-systems",
      "application/x-inst-for-Scientific-info",
      "application/mods+xml",
      "application/rdf+xml",
      "application/x-bibtex",
      "text/x-bibtex",
      "application/marc",
      "application/vnd.citationstyles.style+xml"
    ].join(";")

    File.open("#{Path[staging, "#{@bin}.desktop"]}", "w") do |f|
      INI.build(f, desktop)
    end

    return @config.staging
  end
end
