%global gitrev b4aa5c1
%define confdir %{_sysconfdir}/dnf

Name:		dnf
Version:	0.2.6
Release:	8.git%{gitrev}%{?dist}
Summary:	Package manager forked from Yum, using libsolv as a dependency resolver
Group:		System Environment/Base
License:	GPLv2+
URL:		https://github.com/akozumpl/dnf
Source0:	http://akozumpl.fedorapeople.org/dnf-%{gitrev}.tar.xz
BuildArch:	noarch
BuildRequires:	cmake python2
Requires:	python-hawkey >= 0.2.4-4
Requires:	crontabs

%description
Package manager forked from Yum, using libsolv as a dependency resolver.

%prep
%setup -q -n dnf

%build
%cmake .
make %{?_smp_mflags}

%install
rm -rf $RPM_BUILD_ROOT
make install DESTDIR=$RPM_BUILD_ROOT

%files
%doc README.md COPYING
%{_bindir}/dnf
%{python_sitelib}/dnf/*
%config(noreplace) %{confdir}/dnf.conf
%{_sysconfdir}/cron.hourly/dnf-makecache.cron

%changelog
* Tue Jun 19 2012 Aleš Kozumplík <akozumpl@redhat.com> - 0.2.6-8.gitb4aa5c1
- Fix rpmlint issues.

* Wed Jun 13 2012 Aleš Kozumplík <akozumpl@redhat.com> - 0.2.6-6.git9d95cc5%{?dist}
- Depend on the latest python-hawkey.

* Tue Jun 12 2012 Aleš Kozumplík <akozumpl@redhat.com> - 0.2.6-4.git2791093%{?dist}
- Fix missing cli/__init__.py

* Fri Jun 8 2012 Aleš Kozumplík <akozumpl@redhat.com> - 0.2.6-3	.git365322d%{?dist}
- Logging improvements.

* Wed May 16 2012 Aleš Kozumplík <akozumpl@redhat.com> - 0.2.5-2.gitf594065%{?dist}
- erase: remove dependants along with their dependency.

* Mon May 14 2012 Aleš Kozumplík <akozumpl@redhat.com> - 0.2.4-3.gite3adb52%{?dist}
- Use cron to prefetch metadata.
- Always loads filelists (attempts to fix some resolving problems).

* Mon May 7 2012 Aleš Kozumplík <akozumpl@redhat.com> - 0.2.3-1.gitbbc0801%{?dist}
- Fix assert in hawkey's sack.c.

* Fri May 4 2012 Aleš Kozumplík <akozumpl@redhat.com> - 0.2.2-6.git6787583%{?dist}
- support plain 'dnf update'.
- disable plugins.

* Thu Apr 26 2012 Aleš Kozumplík <akozumpl@redhat.com> - 0.2.1-2.gitde732f5%{?dist}
- Create 'etc/dnf/dnf.conf'.

* Wed Apr 25 2012 Aleš Kozumplík <akozumpl@redhat.com> - 0.2.0-2.git70753dd%{?dist}
- New version.

* Thu Apr 12 2012 Aleš Kozumplík <akozumpl@redhat.com> - 0.1-0.git833c054%{?dist}
- Initial package.
