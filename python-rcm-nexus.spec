Name:		python-rcm-nexus
Version:	2.0.0
Release:	3%{?dist}
Summary:	RCM Tools for Working with the Sonatype Nexus Repository Manager

License:	GNU General Public License Version 3
URL:		https://mojo.redhat.com/docs/DOC-1010179
Source0:	%{name}-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	python-devel python-setuptools

Requires:	python python-setuptools python-lxml python-requests python-click PyYAML npm python-enum34

Obsoletes:	rcm-nexus < 2.0.0

%description
RCM-oriented command line tool and python package for manipulating
Apache Maven repositories hosted on Sonatype Nexus


%prep
%autosetup -n %{name}-%{version}


%build
%{__python} setup.py build


%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install --skip-build --root %{buildroot}


%files
%defattr(-,root,root,-)
%doc LICENSE README.rst
%{python_sitelib}/*
%{_bindir}/*


%changelog
* Mon Oct 12 2020  David Hladky <dhladky at, redhat.com> 2.0.0-3
- NEXUS-326 - Implement Push of NPM Modules to Repository
- NEXUS-329 - Remove Many Warnings in the Code
- NEXUS-338 - Add Checking for Maven/NPM products
- NEXUS-336 - Make User Name and Password Configurable For Each Session or Together
- NEXUS-331 - Add More Parameter Verification
- NEXUS-327 - Update List Products to Process npm Profiles Properly
- NEXUS-340 - Add List of Available Commands to the Utility
- NEXUS-342 - Backport The New Features to Python 2 due to RHEL 6 Compatibility
