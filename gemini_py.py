import subprocess
import shutil
import os

def call_gemini_cli(command_args, use_shell=False):
    """
    Calls the gemini-cli with the given arguments and returns its output.

    Args:
        command_args (list): A list of strings representing the command and its arguments.
        use_shell (bool): If True, the command will be executed through the shell.
                          Use with caution, especially with untrusted input.
    """
    gemini_executable = shutil.which("gemini")
    if gemini_executable:
        # If found, use the absolute path directly
        full_command = [gemini_executable] + command_args[1:] if len(command_args) > 1 else [gemini_executable]
    else:
        print("gemini NOT found by shutil.which in Python's PATH.")
        print("Python's current PATH environment variable:")
        for p in os.environ.get("PATH", "").split(os.pathsep):
            print(f"  - {p}")
        full_command = command_args

    try:
        # Execute the command
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,  # Decode stdout/stderr as text
            check=True,   # Raise an exception for non-zero exit codes
            shell=use_shell # Use shell if specified
        )

        print("\n--- STDOUT ---")
        print(result.stdout)
        return result.stdout

    except subprocess.CalledProcessError as e:
        print(f"\nError calling gemini: {e}")
        print(f"Command: {e.cmd}")
        print(f"Return Code: {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return None
    except FileNotFoundError:
        print("\nError: 'gemini-cli' command not found.")
        print("This usually means the executable is not in Python's effective PATH.")
        return None
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        return None


output_with_shell = call_gemini_cli(["gemini-cli", '-p', 'What makes Australia unique?'], use_shell=True)
