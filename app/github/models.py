from pydantic import BaseModel


class GitHubComment(BaseModel):
    id: int | None = None
    body: str = ""


class GitHubUser(BaseModel):
    login: str


class GitHubRepository(BaseModel):
    name: str
    full_name: str
    owner: GitHubUser


class GitHubIssuePullRequest(BaseModel):
    url: str


class GitHubIssue(BaseModel):
    number: int
    pull_request: GitHubIssuePullRequest | None = None


class IssueCommentPayload(BaseModel):
    action: str | None = None
    comment: GitHubComment
    issue: GitHubIssue
    repository: GitHubRepository
