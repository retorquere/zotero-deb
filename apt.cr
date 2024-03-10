#!/usr/bin/env crystal

require "./staging"
require "time"
require "path"

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

["amd64"].each do |arch|
  [true].each do |beta|
    zotero = Zotero.new("amd64", true)
    staged = zotero.stage

    version = zotero.config.client.version(zotero.version)

    repo = Path["apt"].expand
    deb = Path[repo, "#{zotero.config.package}_#{version}-#{arch}.deb"]
    run "mkdir", ["-p", repo.to_s]
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
    args += [staged]
    run "fpm", args

    changes = Path[deb.dirname, deb.stem + ".changes"]
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
  end
end
