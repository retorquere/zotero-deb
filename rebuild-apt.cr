#!/usr/bin/env crystal

require "./staging"
require "time"
require "path"
require "uri"

require "openssl"

def hash(filename : String | Path, algo : String) : String
  filename = filename.to_s
  digest = OpenSSL::Digest.new(algo)
  File.open(filename) do |file|
    buf = Bytes.new(1024)
    while (read_bytes = file.read(buf)) > 0
      digest.update(buf[0, read_bytes])
    end
  end
  return digest.final.hexstring
end

Repo = Path["apt"].expand.to_s
run "mkdir", ["-p", Repo.to_s]

Keep = [] of String

def fetch(asset : Path)
  download "https://zotero.retorque.re/file/apt-package-archive/#{URI.encode_path(asset.basename)}", asset.to_s
  return File.file?(asset.to_s)
end

def banner(s : String)
  puts "\n\n"
  s = "*** #{s} ***"
  puts "*" * s.size
  puts s
  puts "*" * s.size
end

updated = false
["amd64", "i386"].each do |arch|
  ["beta", "release", "legacy"].each do |mode|
    zotero = Zotero.new(arch, mode)
    version = zotero.config.client.version(zotero.version)
    deb = Path[Repo, "#{zotero.config.package}_#{version}_#{arch}.deb"]
    changes = Path[deb.dirname, deb.stem + ".changes"]

    Keep << deb.basename
    Keep << changes.basename

    if ENV.fetch("BUILD", "") == "true"
      banner "rebuilding #{deb.basename}"
    elsif [deb, changes].all?{|asset| File.exists?(asset)}
      banner "retaining #{deb.basename}"
      next
    elsif fetch(deb) && fetch(changes)
      banner "fetched #{deb.basename} from repo"
      next
    else
      banner "building #{deb.basename}"
    end

    staged = zotero.stage
    run "rm", ["-rf", deb.to_s]

    args = [
      "-s", "dir", "-t", "deb",
      "-C", staged,
      "-p", deb.to_s,
      "--version", version,
      "--name", zotero.config.package
    ]
    zotero.config.client.dependencies.each do |dep|
      args << "-d"
      args << dep
    end
    args += ["--architecture", arch]
    args += ["--maintainer", "#{zotero.config.maintainer.name} <#{zotero.config.maintainer.email}>"]
    args += ["--category", zotero.config.client.section]
    args += ["--description", zotero.config.client.description]
    args += ["--license", zotero.license]
    args += ["--vendor", zotero.vendor]
    args += ["--url", zotero.homepage]
    args += ["."]
    chdir staged do
      run "fpm", args
    end

    File.open(changes.to_s, "w") do |f|
      f.puts "Format: 1.8"
      f.puts "Date: #{Time.local.to_s("%a, %d %b %Y %H:%M:%S %z")}"
      f.puts "Source: #{zotero.config.package}"
      f.puts "Binary: #{zotero.config.package}"
      f.puts "Architecture: #{arch}"
      f.puts "Version: #{version}"
      f.puts "Distribution: unstable"
      f.puts "Urgency: medium"
      f.puts "Maintainer: #{zotero.config.maintainer.email}"
      f.puts "Changed-By: #{zotero.config.maintainer.name}"
      f.puts "Description:"
      f.puts " #{zotero.config.package} - #{zotero.config.client.description}"
      f.puts "Changes:
      f.puts " #{zotero.config.package} (#{shlex_quote(version)}) unstable; urgency=low
      f.puts " ."
      f.puts "   * Version #{version}."
      f.puts "Checksums-Sha1:"
      f.puts " #{hash(deb, "SHA1")} #{File.size(deb.to_s)} {deb}"
      f.puts "Files:"
      f.puts " #{hash(deb, "MD5")} #{File.size(deb.to_s)} #{deb}"
    end
    run "debsign", ["-k#{zotero.config.maintainer.gpgkey}", changes.to_s]
    updated = true
  end
end

def human_readable(size : Int64) : String
  units = %w[B KiB MiB GiB TiB PiB EiB ZiB]
  while size >= 1024 && units.size > 1
    size /= 1024
    units.shift
  end
  return "#{size.round(1)} #{units[0]}"
end

if updated || ENV.fetch("PUBLISH", "") == "true"
  maintainer = Zotero.new("amd64", "release").config.maintainer
  chdir Repo do
    Dir.glob("*.*").sort.each do |asset|
      puts "asset #{asset}"
      if File.file?(asset) && !Keep.includes?(asset)
        puts "removing #{asset}"
        File.delete(asset)
      end
    end

    run "apt-ftparchive packages . | awk 'BEGIN{ok=1} { if ($0 ~ /^E: /) { ok = 0 }; print } END{exit !ok}' > Packages"

    run "rm -rf by-hash"
    run "bzip2 -kf Packages"
    run "apt-ftparchive -o APT::FTPArchive::AlwaysStat=true -o APT::FTPArchive::Release::Codename=./ -o APT::FTPArchive::Release::Acquire-By-Hash=yes release . > Release"

    run "gpg --yes -abs --local-user #{maintainer.gpgkey} -o Release.gpg --digest-algo sha256 Release"
    run "gpg --yes -abs --local-user #{maintainer.gpgkey} --clearsign -o InRelease --digest-algo sha256 Release"

    ["MD5Sum", "SHA1", "SHA256", "SHA512"].each do |hsh|
      run "mkdir -p by-hash/#{hsh}"
      ["Packages", "Packages.bz2"].each do |pkg|
        run "cp #{pkg} by-hash/#{hsh}/#{hash(pkg, hsh.sub("Sum", ""))}"
      end
    end

    File.copy("../zotero-archive-keyring.gpg", "zotero-archive-keyring.pgp")

    banner "building index"
    File.copy("../README.css", "index.css")
    File.open("index.md", "w") do |index|
      index.puts("% Zotero packages for Debian-based systems")
      index.puts(File.read("../README.md"))
      index.puts("\n")

      index.puts("| File name | Size |")
      index.puts("| --------- | ---- |")

      Dir.entries(".").select{|name| !(name =~ /^index[.][a-z]+$/) && File.file?(name) }.sort.each do |name|
        index.puts("| [#{name}](#{URI.encode_path(name)}) | #{human_readable(File.size(name))} |")
      end
    end
    run "pandoc", ["--standalone", "--css=index.css", "-i", "index.md", "-o", "index.html"]
    File.delete("index.md")
  end

  if ENV.fetch("GITHUB_ACTIONS", "") == "true"
    File.open(ENV["GITHUB_OUTPUT"], "a") do |f|
      f.puts("update=true")
    end
  end
end
