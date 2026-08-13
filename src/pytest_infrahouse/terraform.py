import json
import os
import time
from contextlib import contextmanager
from subprocess import PIPE, CalledProcessError, Popen
from typing import IO, Dict, List, Optional, Tuple, Union

from . import DEFAULT_PROGRESS_INTERVAL, LOG

DEFAULT_OPEN_ENCODING = "utf8"
DEFAULT_ENCODING = DEFAULT_OPEN_ENCODING

MAX_RETRIES = 5
BACKOFF_SECONDS = 10


def run_with_retries(
    cmd: List[str],
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    stdout: Union[int, IO, None] = None,
    stderr: Union[int, IO, None] = None,
    max_retries: int = MAX_RETRIES,
    backoff_seconds: int = BACKOFF_SECONDS,
) -> None:
    """
    Run a command, retrying on failure with a linear backoff.

    :param cmd: Command to run.
    :param cwd: Working directory.
    :param env: Dictionary with environment for the process.
    :param stdout: Where to send stdout. Default None (inherit).
    :param stderr: Where to send stderr. Default None (inherit).
    :param max_retries: Maximum number of attempts before giving up.
    :param backoff_seconds: Base number of seconds to wait between attempts
        (multiplied by the attempt number).
    :raise CalledProcessError: if the command still fails after ``max_retries`` attempts.
    """
    attempt = 1
    while True:
        ret, cout, cerr = execute(cmd, stdout=stdout, stderr=stderr, cwd=cwd, env=env)
        if ret == 0:
            LOG.info("Command succeeded on attempt %d", attempt)
            return
        error = CalledProcessError(
            returncode=ret, cmd=" ".join(cmd), output=cout, stderr=cerr
        )
        if attempt >= max_retries:
            LOG.error("Command failed after %d attempts", attempt)
            raise error
        sleep_time = backoff_seconds * attempt
        LOG.warning(
            "Attempt %d failed with %s. Retrying in %ds...", attempt, error, sleep_time
        )
        time.sleep(sleep_time)
        attempt += 1


@contextmanager
def terraform_apply(
    path,
    destroy_after=True,
    json_output=True,
    var_file="terraform.tfvars",
    enable_trace=False,
    max_retries=MAX_RETRIES,
    backoff_seconds=BACKOFF_SECONDS,
):
    """
    Run terraform init and apply, then return a generator.
    If destroy_after is True, run terraform destroy afterward.

    :param path: Path to directory with terraform module.
    :type path: str
    :param destroy_after: Run terraform destroy after context it returned back.
    :type destroy_after: bool
    :param json_output: Yield terraform output result as a dict (available in the context)
    :type json_output: bool
    :param var_file: Path to a file with terraform variables.
    :type var_file: str
    :param enable_trace: If True, it will run ``terraform`` with ``TF_LOG=JSON`` and
        save the terraform trace in ``tf-apply-trace.txt`` and ``tf-destroy-trace.txt``.
        Useful if you want to find out what API calls terraform makes and for other
        debugging.
    :type enable_trace: bool
    :param max_retries: Maximum number of retries for terraform operations.
    :type max_retries: int
    :param backoff_seconds: Number of seconds to wait between retry attempts.
    :type backoff_seconds: int
    :return: If json_output is true then yield the result from terraform_output otherwise nothing.
        Use it in the ``with`` block.
    :raise CalledProcessError: if either of terraform commands still exits with non-zero
        after ``max_retries`` attempts.
    """
    cmds = [
        ["terraform", "init", "-no-color"],
        ["terraform", "get", "-update=true", "-no-color"],
        [
            "terraform",
            "apply",
            f"-var-file={var_file}",
            "-input=false",
            "-auto-approve",
            "-no-color",
        ],
    ]
    env = dict(os.environ)
    if enable_trace:
        env["TF_LOG"] = "JSON"
    try:
        for cmd in cmds:
            stderr = (
                open("tf-apply-trace.txt", "w", encoding=DEFAULT_OPEN_ENCODING)
                if enable_trace
                else None
            )
            run_with_retries(
                cmd,
                stdout=None,
                stderr=stderr,
                cwd=path,
                env=env,
                max_retries=max_retries,
                backoff_seconds=backoff_seconds,
            )
        if json_output:
            yield terraform_output(path)
        else:
            yield

    finally:
        if destroy_after:
            stderr = (
                open("tf-destroy-trace.txt", "w", encoding=DEFAULT_OPEN_ENCODING)
                if enable_trace
                else None
            )
            run_with_retries(
                [
                    "terraform",
                    "destroy",
                    f"-var-file={var_file}",
                    "-input=false",
                    "-auto-approve",
                    "-no-color",
                ],
                stdout=None,
                stderr=stderr,
                cwd=path,
                env=env,
                max_retries=max_retries,
                backoff_seconds=backoff_seconds,
            )


def terraform_output(path: str) -> dict:
    """
    Run terraform output and return the json results as a dict.

    :param path: Path to directory with terraform module.
    :return: dict from terraform output
    """
    cmd = ["terraform", "output", "-json", "-no-color"]
    ret, cout, cerr = execute(cmd, stdout=PIPE, stderr=None, cwd=path)
    if ret:
        raise CalledProcessError(
            returncode=ret, cmd=" ".join(cmd), output=cout, stderr=cerr
        )
    assert cout is not None  # stdout=PIPE guarantees captured output
    return json.loads(cout)


def execute(
    cmd: List[str],
    stdout: Union[int, IO, None] = PIPE,
    stderr: Union[int, IO, None] = PIPE,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[int, Optional[bytes], Optional[bytes]]:
    """
    Execute a command and return a tuple with return code, STDOUT and STDERR.

    :param cmd: Command.
    :param stdout: Where to send stdout. Default PIPE.
    :param stderr: Where to send stderr. Default PIPE.
    :param cwd: Working directory.
    :param env: Dictionary with environment for the process.
    :return: Tuple (return code, STDOUT, STDERR)
    """
    LOG.info("Executing: %s", " ".join(cmd))
    with Popen(cmd, stdout=stdout, stderr=stderr, cwd=cwd, env=env) as proc:
        last_checking = time.time()
        while True:
            if proc.poll() is not None:
                break
            if time.time() - last_checking > DEFAULT_PROGRESS_INTERVAL:
                LOG.info("Still waiting for process to complete.")
                last_checking = time.time()
            time.sleep(1)

        cout, cerr = proc.communicate()
        return proc.returncode, cout, cerr
