# WorldBench Early-Tester Launch Checklist

Status reflects checks completed on July 10, 2026. An unchecked item still needs an owner or a live-environment verification before launch.

## Product and onboarding

- [ ] README CTA visible
- [ ] Website CTA visible
- [ ] Issue template working on the default branch
- [ ] Outside-user issue creation verified with a non-collaborator account
- [ ] Real NanoWM checkpoint proof visible in README
- [ ] Real NanoWM checkpoint proof visible on website

## Validation and links

- [ ] PyPI install tested in a clean environment
- [ ] README links tested
- [ ] Website links tested
- [ ] Documentation links tested
- [x] GitHub release prepared

## Distribution and follow-up

- [ ] Reddit posts published
- [ ] X outreach started
- [ ] LinkedIn outreach started
- [x] Founders Inc. update ready
- [ ] Screenshots ready
- [x] External tester tracking sheet created

## Repository settings to verify

The GitHub API was checked on July 10, 2026:

- `tigee1311/worldbench` is public.
- GitHub Issues are enabled.
- The repository owner account has admin permission.
- An unauthenticated request to the new-issue chooser correctly redirects to GitHub sign-in. A GitHub account is required to submit an issue.
- The structured form and outside-user submission still require manual verification after merge.

The structured tester form becomes available publicly only after this branch is merged into the default branch. The existing repository convention allowed blank issues, so `.github/ISSUE_TEMPLATE/config.yml` keeps `blank_issues_enabled: true`.

## Manual GitHub steps

1. Merge `cleanup/checkpoint-regression-positioning` into the default branch.
2. Sign in with a GitHub account that is not a repository collaborator.
3. Open <https://github.com/tigee1311/worldbench/issues/new/choose>.
4. Confirm that **Test WorldBench on my model** appears, that every required field blocks an incomplete submission, and that the authorization checkbox is required.
5. Confirm repository **Settings > General > Features > Issues** remains enabled.
6. After the production website is deployed, check the checkpoint proof, CTA, documentation, and issue links at desktop and mobile widths.

If Issues are disabled, a repository owner can restore access at **Settings > General > Features > Issues** by selecting the **Issues** checkbox.

## Release checks

Create the 0.4.0 release only after the clean-wheel smoke tests, migration notes, default-branch issue form, and production website are verified.
