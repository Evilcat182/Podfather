%global debug_package %{nil}

Name:           %{pkg_name}
Version:        %{pkg_version}
Release:        1%{?dist}
Summary:        Manage Quadlet containers with Podman

License:        MIT
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  python3
BuildRequires:  python3-pip

%description
Podfather is a CLI tool to build, start, stop, remove, and backup Quadlet-based
Podman containers using systemd integration.

%prep
%autosetup

%build
python3 -m venv .buildenv
. .buildenv/bin/activate
pip install --quiet pyinstaller pyyaml cryptography
pyinstaller --onefile --name podfather src/podfather.py
deactivate

%install
install -D -m 0755 dist/podfather \
    %{buildroot}%{_bindir}/podfather
install -D -m 0644 src/podfather_completion.bash \
    %{buildroot}%{_datadir}/bash-completion/completions/podfather

%files
%{_bindir}/podfather
%{_datadir}/bash-completion/completions/podfather

%changelog
* Sat Apr  4 2026 podfather <podfather@localhost> - 1.0.1-1
- Add backup create/restore commands with encryption support
- Add cryptography dependency

* Thu Apr  2 2026 podfather <podfather@localhost> - 1.0.0-1
- Initial RPM packaging with bash tab completion
