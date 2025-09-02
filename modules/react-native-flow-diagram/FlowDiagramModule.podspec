require "json"

package = JSON.parse(File.read(File.join(__dir__, "package.json")))

Pod::Spec.new do |s|
  s.name         = "FlowDiagramModule"
  s.version      = package["version"]
  s.summary      = package["description"]
  s.homepage     = package["homepage"]
  s.license      = package["license"]
  s.authors      = package["author"]

  s.platforms    = { :ios => min_ios_version_supported }
  s.source       = { :git => ".git", :tag => "#{s.version}" }

  s.source_files = "ios/**/*.{h,m,mm,cpp,swift}"
  s.private_header_files = "ios/**/*.h"

  # Specify Swift version explicitly
  s.swift_version = "5.0"

  # Enable module definition so it can be imported in Swift
  s.module_name = "FlowDiagramModule"
  s.requires_arc = true

  install_modules_dependencies(s)
end
