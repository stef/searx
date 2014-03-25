#!/usr/bin/env python

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
def check(user,repo, path='.', branch="master"):
    behind=0
    msgs=[]
    found=False
    with open('%s/.git/refs/heads/%s' % (path, branch),'r') as fd:
        sha = ' '.join(fd.readline().split())
    r = fetch('https://api.github.com/repos/%s/%s/commits' % (user, repo))
    while True:
        if r.status_code == requests.codes.forbidden:
            print "meh, limited"
            break
        if not r.status_code == requests.codes.ok:
            print "meh, http not ok"
            break
        for c in r.json():
            if c['sha'] == sha:
                return (behind, msgs)
            msgs.append(c['commit']['message'])
            behind+=1
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
    behind, msgs = check(sys.argv[1],
                         sys.argv[2],
                         '.' if len(sys.argv)<4 else sys.argv[3],
                         'master' if len(sys.argv)<5 else sys.argv[4])
    if behind > 0:
        if short:
            print behind
        else:
            print "behind by", behind, "commits:"
            print '\t', '\n\t'.join(msgs)
            print "\nit's time for some git pull origin master"