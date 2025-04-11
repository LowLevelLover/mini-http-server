{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell {
  buildInputs = [
    pkgs.python39        # or whichever python version you are using
    pkgs.pipenv
  ];

  # This hook runs every time you enter the nix shell.
  shellHook = ''
    # This ensures Pipenv will create its own virtualenv,
    # even if it detects you are in a shell-managed environment.
    export PIPENV_IGNORE_VIRTUALENVS=1
    echo "Welcome! Your Nix shell is set up with Python and Pipenv."
  '';
}
