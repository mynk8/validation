# Packit Service validation

For the validation of the Packit Service we run a validation script every night.

The script verifies that Copr builds and Testing farm runs are processed correctly for pull requests in `avant/hello-world` repo:

- comment trigger (each PR with title beginning `Basic test case:` is taken
  and commented with `/packit build`)
- commit (push) trigger - PR with title `Basic test case - commit trigger` is taken and a new empty commit is pushed
- opened PR trigger - new PR is created; source branch `test/{DEPLOYMENT}/opened_pr`,
  after running the test the PR is closed

## Running manually

If you want to run the script on your own:

- Set a `FORGEJO_TOKEN` environment variable holding a [personal access
  token](https://codeberg.org/settings/personal_access_tokens).