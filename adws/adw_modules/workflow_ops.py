"""Core workflow operations extracted from adw_plan_build.py.

This module contains the business logic for planning, building, and
other workflow operations used by the composable ADW scripts.
"""

import glob
import json
import logging
import subprocess
import re
from typing import Tuple, Optional
from adw_modules.data_types import (
    AgentTemplateRequest,
    GitHubIssue,
    AgentPromptResponse,
    IssueClassSlashCommand,
)
from adw_modules.agent import execute_template
from adw_modules.github import get_repo_url, extract_repo_path
from adw_modules.state import ADWState
from adw_modules.utils import parse_json


# Agent name constants
AGENT_PLANNER = "sdlc_planner"
AGENT_IMPLEMENTOR = "sdlc_implementor"
AGENT_CLASSIFIER = "issue_classifier"
AGENT_PLAN_FINDER = "plan_finder"
AGENT_BRANCH_GENERATOR = "branch_generator"
AGENT_PR_CREATOR = "pr_creator"


def format_issue_message(
    adw_id: str, agent_name: str, message: str, session_id: Optional[str] = None
) -> str:
    """Format a message for issue comments with ADW tracking."""
    if session_id:
        return f"{adw_id}_{agent_name}_{session_id}: {message}"
    return f"{adw_id}_{agent_name}: {message}"


def extract_adw_info(text: str, temp_adw_id: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract ADW workflow and ID from text using classify_adw agent.
    Returns (workflow_command, adw_id) tuple."""
    
    # Use classify_adw to extract structured info
    request = AgentTemplateRequest(
        agent_name="adw_classifier",
        slash_command="/classify_adw",
        args=[text],
        adw_id=temp_adw_id,
        model="sonnet",
    )
    
    try:
        response = execute_template(request)
        
        if not response.success:
            print(f"Failed to classify ADW: {response.output}")
            return None, None
        
        # Parse JSON response using utility that handles markdown
        try:
            data = parse_json(response.output, dict)
            adw_command = data.get("adw_slash_command", "").replace("/", "")  # Remove slash
            adw_id = data.get("adw_id")
            
            # Validate command
            valid_workflows = ["adw_plan", "adw_build", "adw_test", "adw_plan_build", "adw_plan_build_test"]
            if adw_command and adw_command in valid_workflows:
                return adw_command, adw_id
            
            return None, None
            
        except ValueError as e:
            print(f"Failed to parse classify_adw response: {e}")
            return None, None
            
    except Exception as e:
        print(f"Error calling classify_adw: {e}")
        return None, None


def classify_issue(
    issue: GitHubIssue, adw_id: str, logger: logging.Logger
) -> Tuple[Optional[IssueClassSlashCommand], Optional[str]]:
    """Classify GitHub issue and return appropriate slash command.
    Returns (command, error_message) tuple."""
    
    # Use the classify_issue slash command template with minimal payload
    # Only include the essential fields: number, title, body
    minimal_issue_json = issue.model_dump_json(
        by_alias=True, 
        include={"number", "title", "body"}
    )
    
    request = AgentTemplateRequest(
        agent_name=AGENT_CLASSIFIER,
        slash_command="/classify_issue",
        args=[minimal_issue_json],
        adw_id=adw_id,
        model="sonnet",
    )
    
    logger.debug(f"Classifying issue: {issue.title}")
    
    response = execute_template(request)
    
    logger.debug(f"Classification response: {response.model_dump_json(indent=2, by_alias=True)}")
    
    if not response.success:
        return None, response.output
    
    # Extract the classification from the response
    output = response.output.strip()
    
    # Look for the classification pattern in the output
    # Claude might add explanation, so we need to extract just the command
    classification_match = re.search(r'(/chore|/bug|/feature|0)', output)
    
    if classification_match:
        issue_command = classification_match.group(1)
    else:
        issue_command = output
    
    if issue_command == "0":
        return None, f"No command selected: {response.output}"
    
    if issue_command not in ["/chore", "/bug", "/feature"]:
        return None, f"Invalid command selected: {response.output}"
    
    return issue_command, None  # type: ignore




def build_plan(
    issue: GitHubIssue, command: str, adw_id: str, logger: logging.Logger
) -> AgentPromptResponse:
    """Build implementation plan for the issue using the specified command."""
    issue_plan_template_request = AgentTemplateRequest(
        agent_name=AGENT_PLANNER,
        slash_command=command,
        args=[str(issue.number), adw_id, issue.model_dump_json(by_alias=True)],
        adw_id=adw_id,
        model="sonnet",
    )

    logger.debug(
        f"issue_plan_template_request: {issue_plan_template_request.model_dump_json(indent=2, by_alias=True)}"
    )

    issue_plan_response = execute_template(issue_plan_template_request)

    logger.debug(
        f"issue_plan_response: {issue_plan_response.model_dump_json(indent=2, by_alias=True)}"
    )

    return issue_plan_response


def get_plan_file(
    plan_output: str, issue_number: str, adw_id: str, logger: logging.Logger
) -> Tuple[Optional[str], Optional[str]]:
    """Get the path to the plan file that was just created.
    Returns (file_path, error_message) tuple."""
    request = AgentTemplateRequest(
        agent_name=AGENT_PLAN_FINDER,
        slash_command="/find_plan_file",
        args=[issue_number, adw_id, plan_output],
        adw_id=adw_id,
        model="sonnet",
    )

    response = execute_template(request)

    if not response.success:
        return None, response.output

    # Clean up the response - get just the file path
    file_path = response.output.strip()

    # Validate it looks like a file path
    if file_path and file_path != "0" and "/" in file_path:
        return file_path, None
    elif file_path == "0":
        return None, "No plan file found in output"
    else:
        # If response doesn't look like a path, return error
        return None, f"Invalid file path response: {file_path}"


def implement_plan(
    plan_file: str, adw_id: str, logger: logging.Logger
) -> AgentPromptResponse:
    """Implement the plan using the /implement command."""
    implement_template_request = AgentTemplateRequest(
        agent_name=AGENT_IMPLEMENTOR,
        slash_command="/implement",
        args=[plan_file],
        adw_id=adw_id,
        model="sonnet",
    )

    logger.debug(
        f"implement_template_request: {implement_template_request.model_dump_json(indent=2, by_alias=True)}"
    )

    implement_response = execute_template(implement_template_request)

    logger.debug(
        f"implement_response: {implement_response.model_dump_json(indent=2, by_alias=True)}"
    )

    return implement_response


def generate_branch_name(
    issue: GitHubIssue,
    issue_class: IssueClassSlashCommand,
    adw_id: str,
    logger: logging.Logger,
) -> Tuple[Optional[str], Optional[str]]:
    """Generate and create a git branch for the issue.
    Returns (branch_name, error_message) tuple."""
    # Remove the leading slash from issue_class for the branch name
    issue_type = issue_class.replace("/", "")

    request = AgentTemplateRequest(
        agent_name=AGENT_BRANCH_GENERATOR,
        slash_command="/generate_branch_name",
        args=[issue_type, adw_id, issue.model_dump_json(by_alias=True)],
        adw_id=adw_id,
        model="sonnet",
    )

    response = execute_template(request)

    if not response.success:
        return None, response.output

    branch_name = response.output.strip()
    logger.info(f"Generated branch name: {branch_name}")
    return branch_name, None


def create_commit(
    agent_name: str,
    issue: GitHubIssue,
    issue_class: IssueClassSlashCommand,
    adw_id: str,
    logger: logging.Logger,
) -> Tuple[Optional[str], Optional[str]]:
    """Create a git commit with a properly formatted message.
    Returns (commit_message, error_message) tuple."""
    # Remove the leading slash from issue_class
    issue_type = issue_class.replace("/", "")

    # Create unique committer agent name by suffixing '_committer'
    unique_agent_name = f"{agent_name}_committer"

    request = AgentTemplateRequest(
        agent_name=unique_agent_name,
        slash_command="/commit",
        args=[agent_name, issue_type, issue.model_dump_json(by_alias=True)],
        adw_id=adw_id,
        model="sonnet",
    )

    response = execute_template(request)

    if not response.success:
        return None, response.output

    commit_message = response.output.strip()
    logger.info(f"Created commit message: {commit_message}")
    return commit_message, None


def create_pull_request(
    branch_name: str,
    issue: Optional[GitHubIssue],
    state: ADWState,
    logger: logging.Logger,
) -> Tuple[Optional[str], Optional[str]]:
    """Create a pull request for the implemented changes.
    Returns (pr_url, error_message) tuple."""
    
    # Get plan file from state (may be None for test runs)
    plan_file = state.get("plan_file") or "No plan file (test run)"
    adw_id = state.get("adw_id")
    
    # If we don't have issue data, try to construct minimal data
    if not issue:
        issue_data = state.get("issue", {})
        issue_json = json.dumps(issue_data) if issue_data else "{}"
    elif isinstance(issue, dict):
        # Try to reconstruct as GitHubIssue model which handles datetime serialization
        from adw_modules.data_types import GitHubIssue
        try:
            issue_model = GitHubIssue(**issue)
            issue_json = issue_model.model_dump_json(by_alias=True)
        except Exception:
            # Fallback: use json.dumps with default str converter for datetime
            issue_json = json.dumps(issue, default=str)
    else:
        issue_json = issue.model_dump_json(by_alias=True)
    
    request = AgentTemplateRequest(
        agent_name=AGENT_PR_CREATOR,
        slash_command="/pull_request",
        args=[branch_name, issue_json, plan_file, adw_id],
        adw_id=adw_id,
        model="sonnet",
    )

    response = execute_template(request)

    if not response.success:
        return None, response.output

    pr_url = response.output.strip()
    logger.info(f"Created pull request: {pr_url}")
    return pr_url, None


def ensure_plan_exists(state: ADWState, issue_number: str) -> str:
    """Find or error if no plan exists for issue.
    Used by adw_build.py in standalone mode."""
    # Check if plan file is in state
    if state.get("plan_file"):
        return state.get("plan_file")
    
    # Check current branch
    from adw_modules.git_ops import get_current_branch
    branch = get_current_branch()
    
    # Look for plan in branch name
    if f"-{issue_number}-" in branch:
        # Look for plan file
        plans = glob.glob(f"specs/*{issue_number}*.md")
        if plans:
            return plans[0]
    
    # No plan found
    raise ValueError(f"No plan found for issue {issue_number}. Run adw_plan.py first.")


def ensure_adw_id(issue_number: str, adw_id: Optional[str] = None, logger: Optional[logging.Logger] = None) -> str:
    """Get ADW ID or create a new one and initialize state.
    
    Args:
        issue_number: The issue number to find/create ADW ID for
        adw_id: Optional existing ADW ID to use
        logger: Optional logger instance
        
    Returns:
        The ADW ID (existing or newly created)
    """
    # If ADW ID provided, check if state exists
    if adw_id:
        state = ADWState.load(adw_id, logger)
        if state:
            if logger:
                logger.info(f"Found existing ADW state for ID: {adw_id}")
            else:
                print(f"Found existing ADW state for ID: {adw_id}")
            return adw_id
        # ADW ID provided but no state exists, create state
        state = ADWState(adw_id)
        state.update(adw_id=adw_id, issue_number=issue_number)
        state.save("ensure_adw_id")
        if logger:
            logger.info(f"Created new ADW state for provided ID: {adw_id}")
        else:
            print(f"Created new ADW state for provided ID: {adw_id}")
        return adw_id
    
    # No ADW ID provided, create new one with state
    from adw_modules.utils import make_adw_id
    new_adw_id = make_adw_id()
    state = ADWState(new_adw_id)
    state.update(adw_id=new_adw_id, issue_number=issue_number)
    state.save("ensure_adw_id")
    if logger:
        logger.info(f"Created new ADW ID and state: {new_adw_id}")
    else:
        print(f"Created new ADW ID and state: {new_adw_id}")
    return new_adw_id


def find_existing_branch_for_issue(issue_number: str, adw_id: Optional[str] = None) -> Optional[str]:
    """Find an existing branch for the given issue number.
    Returns branch name if found, None otherwise."""
    # List all branches
    result = subprocess.run(
        ["git", "branch", "-a"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace"
    )
    
    if result.returncode != 0:
        return None
    
    branches = result.stdout.strip().split('\n')
    
    # Look for branch with standardized pattern: *-issue-{issue_number}-adw-{adw_id}-*
    for branch in branches:
        branch = branch.strip().replace('* ', '').replace('remotes/origin/', '')
        # Check for the standardized pattern
        if f"-issue-{issue_number}-" in branch:
            if adw_id and f"-adw-{adw_id}-" in branch:
                return branch
            elif not adw_id:
                # Return first match if no adw_id specified
                return branch
    
    return None


def find_plan_for_issue(issue_number: str, adw_id: Optional[str] = None) -> Optional[str]:
    """Find plan file for the given issue number and optional adw_id.
    Returns path to plan file if found, None otherwise."""
    import os
    
    # Get project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    agents_dir = os.path.join(project_root, "agents")
    
    if not os.path.exists(agents_dir):
        return None
    
    # If adw_id is provided, check specific directory first
    if adw_id:
        plan_path = os.path.join(agents_dir, adw_id, AGENT_PLANNER, "plan.md")
        if os.path.exists(plan_path):
            return plan_path
    
    # Otherwise, search all agent directories
    for agent_id in os.listdir(agents_dir):
        agent_path = os.path.join(agents_dir, agent_id)
        if os.path.isdir(agent_path):
            plan_path = os.path.join(agent_path, AGENT_PLANNER, "plan.md")
            if os.path.exists(plan_path):
                # Check if this plan is for our issue by reading branch info or checking commits
                # For now, return the first plan found (can be improved)
                return plan_path
    
    return None


def create_or_find_branch(
    issue_number: str,
    issue: GitHubIssue,
    state: ADWState,
    logger: logging.Logger
) -> Tuple[str, Optional[str]]:
    """Create or find a branch for the given issue.
    
    1. First checks state for existing branch name
    2. Then looks for existing branches matching the issue
    3. If none found, classifies the issue and creates a new branch
    
    Returns (branch_name, error_message) tuple.
    """
    # 1. Check state for branch name
    branch_name = state.get("branch_name") or state.get("branch", {}).get("name")
    if branch_name:
        logger.info(f"Found branch in state: {branch_name}")
        # Check if we need to checkout
        from adw_modules.git_ops import get_current_branch
        current = get_current_branch()
        if current != branch_name:
            result = subprocess.run(["git", "checkout", branch_name], capture_output=True, text=True, encoding="utf-8", errors="replace")
            if result.returncode != 0:
                # Branch might not exist locally, try to create from remote
                result = subprocess.run(["git", "checkout", "-b", branch_name, f"origin/{branch_name}"], 
                                      capture_output=True, text=True, encoding="utf-8", errors="replace")
                if result.returncode != 0:
                    return "", f"Failed to checkout branch: {result.stderr}"
        return branch_name, None
    
    # 2. Look for existing branch
    adw_id = state.get("adw_id")
    existing_branch = find_existing_branch_for_issue(issue_number, adw_id)
    if existing_branch:
        logger.info(f"Found existing branch: {existing_branch}")
        # Checkout the branch
        result = subprocess.run(["git", "checkout", existing_branch], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            return "", f"Failed to checkout branch: {result.stderr}"
        state.update(branch_name=existing_branch)
        return existing_branch, None
    
    # 3. Create new branch - classify issue first
    logger.info("No existing branch found, creating new one")
    
    # Classify the issue
    issue_command, error = classify_issue(issue, adw_id, logger)
    if error:
        return "", f"Failed to classify issue: {error}"
    
    state.update(issue_class=issue_command)
    
    # Generate branch name
    branch_name, error = generate_branch_name(issue, issue_command, adw_id, logger)
    if error:
        return "", f"Failed to generate branch name: {error}"
    
    # Create the branch
    from adw_modules.git_ops import create_branch
    success, error = create_branch(branch_name)
    if not success:
        return "", f"Failed to create branch: {error}"
    
    state.update(branch_name=branch_name)
    logger.info(f"Created and checked out new branch: {branch_name}")
    
    return branch_name, None