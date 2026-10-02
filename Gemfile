# frozen_string_literal: true

# Release tooling shared by the iOS App Store and Android Google Play pipelines
# (docs/ios-app-store-release.md, docs/android-play-store-release.md). Bundler finds
# this Gemfile from ios/EthosProtocol and android/, so both use one pinned fastlane.
# Pinned to an exact version so CI and local runs resolve the same fastlane;
# bump deliberately and commit the regenerated Gemfile.lock.
source "https://rubygems.org"

gem "fastlane", "2.240.1"
