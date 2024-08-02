{ pkgs ? import <nixpkgs> {}}:

pkgs.mkShell {
  packages = [
    pkgs.git
    pkgs.just
    pkgs.python312
    pkgs.poetry
    pkgs.git-cliff
  ];
}