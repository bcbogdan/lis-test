LIS_NEXT_REPO_URL = 'https://github.com/LIS/lis-next.git'
LINUX_REPO_URL = 'https://github.com/torvalds/linux.git'
LINUX_NEXT_REMOTE = 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git'
BUILDS_PATH = '/root/builds'
# Mapping between linux repo files
# and lis-next files
FILES_MAP = {
    "drivers/hv": "hv/",
    "tools/hv": "hv/tools/",
    "drivers/net/hyperv": "hv/"
}