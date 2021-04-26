%if 0%{?fedora} || 0%{?rhel} > 8
%bcond_without server
%bcond_without docs
%else
# For EPEL8 we build only the CLI, not the server bits,
# because Flask and other dependencies are too old.
%bcond_with server
%bcond_with docs
%endif

Name:           waiverdb
Version:        1.3.0
Release:        1%{?dist}
Summary:        Service for waiving results in ResultsDB
License:        GPLv2+
URL:            https://pagure.io/waiverdb
Source0:        https://files.pythonhosted.org/packages/source/w/%{name}/%{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  make
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools

%if %{with server}
BuildRequires:  python3-sphinx
BuildRequires:  python3-sphinxcontrib-httpdomain
BuildRequires:  python3-flask
BuildRequires:  python3-sqlalchemy
BuildRequires:  python3-flask-cors
BuildRequires:  python3-flask-restful
BuildRequires:  python3-flask-sqlalchemy
BuildRequires:  python3-psycopg2
BuildRequires:  python3-gssapi
BuildRequires:  python3-requests-gssapi
BuildRequires:  python3-pytest
BuildRequires:  python3-mock
BuildRequires:  python3-flask-oidc
BuildRequires:  python3-click
BuildRequires:  python3-flask-migrate
BuildRequires:  python3-stomppy
BuildRequires:  python3-fedora-messaging
BuildRequires:  python3-prometheus_client
BuildRequires:  python3-six
Requires:       python3-flask
Requires:       python3-sqlalchemy
Requires:       python3-flask-cors
Requires:       python3-flask-restful
Requires:       python3-flask-sqlalchemy
Requires:       python3-psycopg2
Requires:       python3-gssapi
Requires:       python3-requests-gssapi
Requires:       python3-mock
Requires:       python3-flask-oidc
Requires:       python3-click
Requires:       python3-flask-migrate
Requires:       python3-stomppy
Requires:       python3-fedora-messaging
Requires:       python3-prometheus_client
Requires:       waiverdb-common = %{version}-%{release}
%endif

%description
WaiverDB is a companion service to ResultsDB, for recording waivers
against test results.

%package common
Summary: Common resources for WaiverDB subpackages.

%description common
This package is not useful on its own.  It contains common filesystem resources
for other WaiverDB subpackages.

%package cli
Summary: A CLI tool for interacting with waiverdb
BuildRequires:  python3-click
BuildRequires:  python3-requests-gssapi
Requires:       python3-click
Requires:       python3-requests-gssapi

Requires:       waiverdb-common = %{version}-%{release}

%description cli
This package contains a CLI tool for interacting with waiverdb.

Primarily, submitting new waiverdbs.

%prep
%setup -q -n %{name}-%{version}

# We guard against version flask-restful=0.3.6 in requirements.txt,
# but the version in Fedora is patched to work.
sed -i '/Flask-RESTful/d' requirements.txt

# Replace any staging urls with prod ones
sed -i 's/\.stg\.fedoraproject\.org/.fedoraproject.org/g' conf/client.conf.example

%build
%py3_build
%if %{with docs}
make -C docs html man text
%endif

%install
%py3_install

%if ! %{with server}
# Need to properly split out the client one day...
rm %{buildroot}%{_bindir}/waiverdb
ls -d %{buildroot}%{python3_sitelib}/waiverdb/* | grep -E -v '(__init__.py|cli.py)$' | xargs rm -r
%endif

install -d %{buildroot}%{_sysconfdir}/waiverdb/
install -m0644 \
    conf/client.conf.example \
    %{buildroot}%{_sysconfdir}/waiverdb/client.conf

%if %{with docs}
install -D -m0644 \
    docs/_build/man/waiverdb-cli.1 \
    %{buildroot}%{_mandir}/man1/waiverdb-cli.1

install -D -m0644 \
    docs/_build/man/client.conf.5 \
    %{buildroot}%{_mandir}/man5/waiverdb-client.conf.5

install -D -m0644 \
    docs/_build/man/waiverdb.7 \
    %{buildroot}%{_mandir}/man7/waiverdb.7
%endif

# Tests don't make sense here now that we require postgres to run them.
#%%check
#export PYTHONPATH=%%{buildroot}/%%{python3_sitelib}
#py.test-3 tests/

%if %{with server}
%files
%{python3_sitelib}/%{name}
%exclude %{python3_sitelib}/%{name}/__init__.py
%exclude %{python3_sitelib}/%{name}/__pycache__/__init__.*pyc
%exclude %{python3_sitelib}/%{name}/cli.py
%exclude %{python3_sitelib}/%{name}/__pycache__/cli.*.pyc
%attr(755,root,root) %{_bindir}/waiverdb
%endif

%files common
%license COPYING
%doc README.md conf
%if %{with docs}
%doc docs/_build/html docs/_build/text
%endif
%dir %{python3_sitelib}/%{name}
%dir %{python3_sitelib}/%{name}/__pycache__
%{python3_sitelib}/%{name}/__init__.py
%{python3_sitelib}/%{name}/__pycache__/__init__.*pyc
%{python3_sitelib}/%{name}*.egg-info

%files cli
%license COPYING
%{python3_sitelib}/%{name}/cli.py
%{python3_sitelib}/%{name}/__pycache__/cli.*.pyc
%attr(755,root,root) %{_bindir}/waiverdb-cli
%config(noreplace) %{_sysconfdir}/waiverdb/client.conf

%if %{with docs}
%{_mandir}/man1/waiverdb-cli.1*
%{_mandir}/man5/waiverdb-client.conf.5*
%{_mandir}/man7/waiverdb.7*
%endif

%changelog
