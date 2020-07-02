# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (sort of. It's early days, and there may be some breaking changes released under a minor version increment).

## [0.35.0] - 2020-07-02

### Fixed

- Only import kenlm if asked 

## [0.31.0] - 2020-06-23

- Oops forgot to update this for quite a while. See the README for these changes. Will try to add this updating to the CI/CD... one day.

## [0.5.0] - 2020-01-02

### Changed

- updated `requirements-dev.txt` to have all needed requirements for development

- `replacy/db.py:get_forms_lookup` and `replacy/db.py:get_match_dict` now each accept one parameter - the path to the resource they will load. The default value of this parameter is the value that was previously hardcoded.

- `replacy/__init__.py:ReplaceMatcher.__init__` now does not require a `match_dict` to be passed in as the second parameter. If no `match_dict` is passed, it will load one by calling `replacy/db.py:get_match_dict()` (with no parameter, so it will look in the default location).

## [0.4.0] - 2019-12-UNK

### UNK

## [0.1.0 - 0.3.0] - 2019-12-18

### First

- first pypi release
