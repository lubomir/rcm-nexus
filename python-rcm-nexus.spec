Name:		python-rcm-nexus
Version:	1.1.0
Release:	1%{?dist}
Summary:	RCM Tools for Working with the Sonatype Nexus Repository Manager

License:	GNU General Public License Version 3
URL:		https://mojo.redhat.com/docs/DOC-1010179
Source0:	%{name}-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	python2-devel python-setuptools

Requires:	python2 python-setuptools python-lxml python-requests python-click PyYAML


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