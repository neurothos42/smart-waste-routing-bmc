# Changelog

## [1.0.0] - 2026-11-15
### Added
- Environment-based configuration via `.env` and `.env.example`.
- Automated Pytest test suite (`tests/test_routing.py`) and GitHub Actions CI pipeline.
- MIT License, architecture documentation, and contribution guidelines.

### Fixed
- Fixed accidental user session logout when navigating to `/moving_truck`.
- Connected the UI animation speed selector (`Slow`, `Normal`, `Fast`) in `moving-truck.js`.
- Prevented duplicate CSV rows and oversized PDF exports by clearing `cycle_data` after every 60-cycle flush.
- Renamed `goggle_map.png` to `login_bg_map.png` and removed broken `truck-icon.png` reference.