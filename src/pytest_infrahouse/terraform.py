import json
import logging
import os
import time
from contextlib import contextmanager
from subprocess import PIPE, Popen, CalledProcessError

DEFAULT_OPEN_ENCODING = "utf8"
DEFAULT_ENCODING = DEFAULT_OPEN_ENCODING
DEFAULT_PROGRESS_INTERVAL = 10
LOG = logging.getLogger()


@contextmanager
def terraform_apply(
    path,
    destroy_after=True,
    json_output=True,
    var_file="terraform.tfvars",
    enable_trace=False,
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
    :return: If json_output is true then yield the result from terraform_output otherwise nothing.
        Use it in the ``with`` block.
    :raise CalledProcessError: if either of terraform commands (except ``terraform destroy``)
        exits with non-zero.
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
            ret, cout, cerr = execute(
                cmd, stdout=None, stderr=stderr, cwd=path, env=env
            )
            if ret:
                raise CalledProcessError(
                    returncode=ret, cmd=" ".join(cmd), output=cout, stderr=cerr
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
            execute(
                [
                    "terraform",
                    "destroy",
                    f"-var-file={var_file}",
                    "-input=false",
                    "-auto-approve",
                ],
                stdout=None,
                stderr=stderr,
                cwd=path,
                env=env,
            )


def terraform_output(path):
    """
    Run terraform output and return the json results as a dict.

    :param path: Path to directory with terraform module.
    :type path: str
    :return: dict from terraform output
    :rtype: dict
    """
    cmd = ["terraform", "output", "-json"]
    ret, cout, cerr = execute(cmd, stdout=PIPE, stderr=None, cwd=path)
    if ret:
        raise CalledProcessError(
            returncode=ret, cmd=" ".join(cmd), output=cout, stderr=cerr
        )
    return json.loads(cout)


def execute(
    cmd,
    stdout=PIPE,
    stderr=PIPE,
    cwd=None,
    env=None,
):
    """
    Execute a command and return a tuple with return code, STDOUT and STDERR.

    :param cmd: Command.
    :type cmd: list
    :param stdout: Where to send stdout. Default PIPE.
    :type stdout: int, None
    :param stderr: Where to send stdout. Default PIPE.
    :type stderr: int, None
    :param cwd: Working directory.
    :type cwd: str
    :param env: Dictionary with environment for the process.
    :type env: dict
    :return: Tuple (return code, STDOUT, STDERR)
    :rtype: tuple
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
