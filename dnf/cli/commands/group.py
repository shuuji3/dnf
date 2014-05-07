# group.py
# Group CLI command.
#
# Copyright (C) 2012-2014  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#

from __future__ import absolute_import
from __future__ import unicode_literals
from .. import commands
from dnf.i18n import _, ucd

import dnf.cli
import dnf.exceptions
import dnf.util
import logging
import operator

logger = logging.getLogger("dnf")

def _ensure_grp_arg(cli, basecmd, extcmds):
    """Verify that *extcmds* contains the name of at least one group for
    *basecmd* to act on.

    :param base: a :class:`dnf.Base` object.
    :param basecmd: the name of the command being checked for
    :param extcmds: a list of arguments passed to *basecmd*
    :raises: :class:`cli.CliError`
    """
    if len(extcmds) == 0:
        cli.logger.critical(_('Error: Need a group or list of groups'))
        commands.err_mini_usage(cli, basecmd)
        raise dnf.cli.CliError


class CompsQuery(object):

    AVAILABLE = 1
    INSTALLED = 2

    ENVIRONMENTS = 1
    GROUPS = 2

    def __init__(self, comps, prst, kinds, status):
        self.comps = comps
        self.prst = prst
        self.kinds = kinds
        self.status = status

    def _get(self, items, persistence_fn):
        lst = []
        for it in items:
            installed = persistence_fn(it.id).installed
            if self.status & self.INSTALLED and installed:
                lst.append(it)
            if self.status & self.AVAILABLE and not installed:
                lst.append(it)
        return lst

    def get(self, *patterns):
        res = dnf.util.Bunch()
        res.environments = []
        res.groups = []
        for pat in patterns:
            envs = grps = None
            if self.kinds & self.ENVIRONMENTS:
                envs = self._get(self.comps.environments_by_pattern(pat),
                                 self.prst.environment)
                res.environments.extend(envs)
            if self.kinds & self.GROUPS:
                grps = self._get(self.comps.groups_by_pattern(pat),
                                 self.prst.group)
                res.groups.extend(grps)
            if not envs and not grps:
                msg = _("No relevant match for the specified '%s'.")
                msg = msg % ucd(pat)
                raise dnf.cli.CliError(msg)
        return res


class GroupCommand(commands.Command):
    """ Single sub-command interface for most groups interaction. """

    direct_commands = {'grouplist'    : 'list',
                       'groupinstall' : 'install',
                       'groupupdate'  : 'install',
                       'groupremove'  : 'remove',
                       'grouperase'   : 'remove',
                       'groupinfo'    : 'info'}
    aliases = ('group', 'groups') + tuple(direct_commands.keys())
    summary = _("Display, or use, the groups information")
    usage = "[list|info|summary|install|upgrade|remove|mark] [%s]" % _('GROUP')

    _CMD_ALIASES = {'update'     : 'upgrade',
                    'erase'      : 'remove'}
    _MARK_CMDS = ('install', 'remove')


    @staticmethod
    def _grp_cmd(extcmds):
        return extcmds[0], extcmds[1:]

    @staticmethod
    def _split_extcmds(extcmds):
        if extcmds[0] == 'with-optional':
            types = tuple(dnf.const.GROUP_PACKAGE_TYPES + ('optional',))
            return types, extcmds[1:]
        return dnf.const.GROUP_PACKAGE_TYPES, extcmds

    @classmethod
    def canonical(cls, command_list):
        first = command_list[0]
        rest = command_list[1:]

        cmd = cls.direct_commands.get(first)
        if cmd is None:
            cmd = 'summary'
            if rest:
                cmd = rest.pop(0)
        cmd = cls._CMD_ALIASES.get(cmd, cmd)

        rest.insert(0, cmd)
        return ('groups', rest)

    def __init__(self, cli):
        super(GroupCommand, self).__init__(cli)

    def _assert_comps(self):
        msg = _('No group data available for configured repositories.')
        if not len(self.base.comps):
            raise dnf.exceptions.CompsError(msg)

    def _environment_lists(self, patterns):
        def installed_pred(env):
            return self.base.group_persistor.environment(env.id).installed

        self._assert_comps()
        if patterns is None:
            envs = self.base.comps.environments
        else:
            envs = self.base.comps.environments_by_pattern(",".join(patterns))

        available, installed = dnf.util.partition(installed_pred, envs)

        sort_fn = operator.attrgetter('ui_name')
        return sorted(installed, key=sort_fn), sorted(available, key=sort_fn)

    def _group_lists(self, uservisible, patterns):
        def installed_pred(group):
            return self.base.group_persistor.group(group.id).installed
        installed = []
        available = []

        self._assert_comps()

        if patterns is None:
            grps = self.base.comps.groups
        else:
            grps = self.base.comps.groups_by_pattern(",".join(patterns))
        for grp in grps:
            tgt_list = available
            if installed_pred(grp):
                tgt_list = installed
            if not uservisible or grp.uservisible:
                tgt_list.append(grp)

        sort_fn = operator.attrgetter('ui_name')
        return sorted(installed, key=sort_fn), sorted(available, key=sort_fn)

    def _grp_setup(self):
        try:
            comps = self.base.read_comps()
        except dnf.exceptions.Error as e:
            return 1, [str(e)]
        if not comps:
            return 1, [_('No Groups Available in any repository')]

    def _info(self, userlist):
        for strng in userlist:
            group_matched = False
            for group in self.base.comps.groups_by_pattern(strng):
                self.output.displayPkgsInGroups(group)
                group_matched = True

            if not group_matched:
                logger.error(_('Warning: Group %s does not exist.'), strng)

        return 0, []

    def _install(self, extcmds):
        types, patterns = self._split_extcmds(extcmds)
        q = CompsQuery(self.base.comps, self.base.group_persistor,
                       CompsQuery.ENVIRONMENTS | CompsQuery.GROUPS,
                       CompsQuery.AVAILABLE)
        res = q.get(*patterns)
        for env in res.environments:
            self.base.environment_install(env, types)
        for grp in res.groups:
            self.base.group_install(grp, types)

    def _list(self, userlist):
        uservisible = 1

        if len(userlist) > 0:
            if userlist[0] == 'hidden':
                uservisible = 0
                userlist.pop(0)
        if not userlist:
            userlist = None # Match everything...

        env_inst, env_avail = self._environment_lists(userlist)
        installed, available = self._group_lists(uservisible, userlist)

        if not any([env_inst, env_avail, installed, available]):
            logger.error(_('Warning: No groups match: %s'),
                              ", ".join(userlist))
            return 0, []

        def _out_grp(sect, group):
            if not done:
                logger.info(sect)
            msg = '   %s' % group.ui_name
            if self.base.conf.verbose:
                msg += ' (%s)' % group.id
            if group.lang_only:
                msg += ' [%s]' % group.lang_only
            logger.info('%s', msg)

        def _out_env(sect, envs):
            if envs:
                logger.info(sect)
            for e in envs:
                msg = '   %s' % e.ui_name
                if self.base.conf.verbose:
                    msg += ' (%s)' % e.id
                logger.info(msg)

        _out_env(_('Available environment groups:'), env_avail)
        _out_env(_('Installed environment groups:'), env_inst)

        done = False
        for group in installed:
            if group.lang_only:
                continue
            _out_grp(_('Installed groups:'), group)
            done = True

        done = False
        for group in installed:
            if not group.lang_only:
                continue
            _out_grp(_('Installed language groups:'), group)
            done = True

        done = False
        for group in available:
            if group.lang_only:
                continue
            _out_grp(_('Available groups:'), group)
            done = True

        done = False
        for group in available:
            if not group.lang_only:
                continue
            _out_grp(_('Available language groups:'), group)
            done = True

        return 0, []

    def _mark_install(self, patterns):
        persistor = self.base.group_persistor
        q = CompsQuery(self.base.comps, persistor,
                       CompsQuery.GROUPS | CompsQuery.ENVIRONMENTS,
                       CompsQuery.AVAILABLE)
        solver = self.base.build_comps_solver()
        res = q.get(*patterns)
        types = dnf.comps.DEFAULT | dnf.comps.MANDATORY | dnf.comps.OPTIONAL
        for env in res.environments:
            solver.environment_install(env, types, None)
        if res.environments:
            logger.info(_('Environments marked installed: %s'),
                        ','.join([g.ui_name for g in res.environments]))
        for grp in res.groups:
            solver.group_install(grp, types, None)
        if res.groups:
            logger.info(_('Groups marked installed: %s'),
                        ','.join([g.ui_name for g in res.groups]))
        persistor.commit()

    def _mark_remove(self, patterns):
        persistor = self.base.group_persistor
        q = CompsQuery(self.base.comps, persistor,
                       CompsQuery.GROUPS | CompsQuery.ENVIRONMENTS,
                       CompsQuery.INSTALLED)
        solver = self.base.build_comps_solver()
        res = q.get(*patterns)
        for env in res.environments:
            solver.environment_remove(env)
        if res.environments:
            logger.info(_('Environments marked removed: %s'),
                        ','.join([g.ui_name for g in res.environments]))
        for grp in res.groups:
            solver.group_remove(grp)
        if res.groups:
            logger.info(_('Groups marked removed: %s'),
                        ','.join([g.ui_name for g in res.groups]))
        persistor.commit()

    def _mark_subcmd(self, extcmds):
        if extcmds[0] in self._MARK_CMDS:
            return extcmds[0], extcmds[1:]
        return 'install', extcmds

    def _remove(self, patterns):
        q = CompsQuery(self.base.comps, self.base.group_persistor,
                       CompsQuery.ENVIRONMENTS | CompsQuery.GROUPS,
                       CompsQuery.INSTALLED)
        res = q.get(*patterns)

        for env in res.environments:
            self.base.environment_remove(env)
        for grp in res.groups:
            self.base.group_remove(grp)

    def _summary(self, userlist):
        uservisible = 1
        if len(userlist) > 0:
            if userlist[0] == 'hidden':
                uservisible = 0
                userlist.pop(0)
        if not userlist:
            userlist = None # Match everything...

        installed, available = self._group_lists(uservisible, userlist)

        def _out_grp(sect, num):
            if not num:
                return
            logger.info('%s %u', sect, num)
        done = 0
        for group in installed:
            if group.lang_only:
                continue
            done += 1
        _out_grp(_('Installed Groups:'), done)

        done = 0
        for group in installed:
            if not group.lang_only:
                continue
            done += 1
        _out_grp(_('Installed Language Groups:'), done)

        done = False
        for group in available:
            if group.lang_only:
                continue
            done += 1
        _out_grp(_('Available Groups:'), done)

        done = False
        for group in available:
            if not group.lang_only:
                continue
            done += 1
        _out_grp(_('Available Language Groups:'), done)

        return 0, []

    def _upgrade(self, patterns):
        q = CompsQuery(self.base.comps, self.base.group_persistor,
                       CompsQuery.GROUPS, CompsQuery.INSTALLED)
        res = q.get(*patterns)
        cnt = 0
        for grp in res.groups:
            cnt += self.base.group_upgrade(grp)
        if not cnt:
            msg = _('No packages marked for upgrade.')
            raise dnf.cli.CliError(msg)

    def configure(self, extcmds):
        cmd = extcmds[0]
        demands = self.cli.demands
        demands.available_repos = True
        demands.sack_activation = True
        if cmd in ('install', 'mark', 'remove', 'upgrade'):
            demands.root_user = True

    def doCheck(self, basecmd, extcmds):
        """Verify that conditions are met so that this command can run.
        The exact conditions checked will vary depending on the
        subcommand that is being called.

        :param basecmd: the name of the command
        :param extcmds: the command line arguments passed to *basecmd*
        """
        cmd, extcmds = self._grp_cmd(extcmds)

        commands.checkEnabledRepo(self.base)

        if cmd in ('install', 'remove', 'mark', 'info'):
            _ensure_grp_arg(self.cli, cmd, extcmds)

        if cmd in ('install', 'upgrade'):
            commands.checkGPGKey(self.base, self.cli)

        cmds = ('list', 'info', 'remove', 'install', 'upgrade', 'summary', 'mark')
        if cmd not in cmds:
            logger.critical(_('Invalid groups sub-command, use: %s.'),
                                 ", ".join(cmds))
            raise dnf.cli.CliError

    def run(self, extcmds):
        cmd, extcmds = self._grp_cmd(extcmds)

        self._grp_setup()

        if cmd == 'summary':
            return self._summary(extcmds)
        if cmd == 'list':
            return self._list(extcmds)
        if cmd == 'info':
            return self._info(extcmds)
        if cmd == 'mark':
            (subcmd, extcmds) = self._mark_subcmd(extcmds)
            if subcmd == 'remove':
                return self._mark_remove(extcmds)
            else:
                assert subcmd == 'install'
                return self._mark_install(extcmds)

        self.cli.demands.resolving = True
        if cmd == 'install':
            return self._install(extcmds)
        if cmd == 'upgrade':
            return self._upgrade(extcmds)
        if cmd == 'remove':
            return self._remove(extcmds)
