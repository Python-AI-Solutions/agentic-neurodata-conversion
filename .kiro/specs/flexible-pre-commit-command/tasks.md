# Implementation Plan

- [x] 1. Update pixi.toml pre-commit task definition
  - Modify the pre-commit task to remove the hardcoded `--all-files` flag
  - Change from `"pre-commit run --all-files"` to `"pre-commit run"`
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 3.1, 3.2_

- [x] 2. Update pre-commit-guide.md documentation
  - Update command examples to show explicit `--all-files` usage
  - Add examples of passing custom arguments with `--` separator
  - Update the daily workflow section to reflect new usage patterns
  - _Requirements: 2.3, 3.3_

- [x] 3. Update development-essentials.md documentation
  - Update the quick commands section to show new pre-commit usage
  - Modify daily workflow examples to use explicit flags
  - Update troubleshooting section if needed
  - _Requirements: 2.3, 3.3_

- [ ] 4. Test the updated pre-commit command functionality
  - Test `pixi run pre-commit` (default behavior)
  - Test `pixi run pre-commit -- --all-files` (explicit all files)
  - Test `pixi run pre-commit -- --files specific_file.py` (specific files)
  - Test `pixi run pre-commit -- --hook-stage manual` (hook-specific)
  - Verify error handling for invalid arguments
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 3.1, 3.2, 3.3_
