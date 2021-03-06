#!/usr/bin/env python

# checks how many commits a local repo is behind a master repo on github:
#   python gcheck.py asciimoo searx /home/searx/
# should return you a list of commit msgs that are waiting to be
# pulled from asciimoos searx repo

# searx is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# searx is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with searx. If not, see < http://www.gnu.org/licenses/ >.
# (C) 2012 by Stefan Marsiske, <s@ctrlc.hu>

import requests, re, hashlib, os
from cPickle import load, dump

def fetch(url, cachedir = '/tmp/ghcheck'):
    cname = '%s/%s' % (cachedir, hashlib.sha256(url).hexdigest())
    if not os.path.exists(cachedir):
        os.mkdir(cachedir)
    if not os.path.exists(cname):
        r = requests.get(url)
        with open(cname, 'w') as fd:
            dump(r, fd)
        return r
    with open(cname, 'r') as fd:
        cached = load(fd)

    r = requests.get(url, headers = {'If-None-Match': cached.headers['ETag']})
    if r.status_code == requests.codes.not_modified:
        return cached
    elif r.status_code == requests.codes.ok:
        with open(cname, 'w') as fd:
            dump(r, fd)
        return r
    raise r.status_code

pagere=re.compile(r'<(https://api.github.com/repositories/[^>]*)>; rel="next"')

def get_hashes(repo, cachedir = '/tmp/ghcheck'):
    cname = '%s/%s' % (cachedir, hashlib.sha256(repo).hexdigest())
    if not os.path.exists(cname):
        return []
    ret = []
    with open(cname, 'r') as fd:
        r = load(fd)
    while True:
        for c in r.json():
            ret.append(c['sha'])
        m = pagere.match(r.headers['link'])
        if m:
            #print m.group(1)
            cname = '%s/%s' % (cachedir, hashlib.sha256(m.group(1)).hexdigest())
            with open(cname,  'r') as fd:
                if not os.path.exists(cname):
                    return ret
                r = load(fd)
        else:
            break
    return ret

def check(user,repo, path='.', branch="master"):
    msgs=[]
    found=False
    with open('%s/.git/refs/heads/%s' % (path, branch),'r') as fd:
        sha = ' '.join(fd.readline().split())
    hashes = get_hashes('https://api.github.com/repos/%s/%s/commits' % (user, repo))
    if len(hashes)>0 and sha not in hashes:
        return (-1, ['locally modified'])
    r = fetch('https://api.github.com/repos/%s/%s/commits' % (user, repo))
    while True:
        if r.status_code == requests.codes.forbidden:
            print "meh, rate-limited"
            break
        if not r.status_code == requests.codes.ok:
            print "meh, http not ok"
            break
        for c in r.json():
            if c['sha'] == sha:
                return msgs
            msgs.append(c['commit']['message'])
        m = pagere.match(r.headers['link'])
        if m:
            #print m.group(1)
            r = fetch(m.group(1))
        else:
            break
    return (0, [])

if __name__ == "__main__":
    import sys
    short=False
    if '-s' in sys.argv:
        short = True
        del sys.argv[sys.argv.index('-s')]
    if len(sys.argv) < 3:
        print "usage:", sys.argv[0], "[-s] <github-user> <github-repo> [<local-repo-path>] [<github branch>]"
        sys.exit(1)
    msgs = check(sys.argv[1],
                 sys.argv[2],
                 '.' if len(sys.argv)<4 else sys.argv[3],
                 'master' if len(sys.argv)<5 else sys.argv[4])
    if len(msgs) > 0:
        if short:
            print len(msgs)
        else:
            print "behind by", len(msgs), "commits:"
            print '\t', '\n\t'.join(msgs)
            print "\nit's time for some git pull origin master"
