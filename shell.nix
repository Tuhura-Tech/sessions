with import <nixpkgs> {};
mkShell {
  buildInputs = [
    python313
    uv
    nodejs
    pnpm
    playwright-driver.browsers
    act
  ];

  NIX_LD_LIBRARY_PATH = lib.makeLibraryPath [
    stdenv.cc.cc
  ];
  NIX_LD = lib.fileContents "${stdenv.cc}/nix-support/dynamic-linker";
  shellHook = ''
      export LD_LIBRARY_PATH=$NIX_LD_LIBRARY_PATH
      export PLAYWRIGHT_BROWSERS_PATH=${pkgs.playwright-driver.browsers}
      export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
      export PLAYWRIGHT_HOST_PLATFORM_OVERRIDE="ubuntu-24.04"
    '';
}