#!/bin/bash
# macOS disk triage — read-only diagnostic. Deletes nothing.
# Usage:
#   disk-triage.sh            full triage report
#   disk-triage.sh rate PATH  measure growth rate of PATH over 30s
export LC_ALL=C

hr() { printf '\n\033[1m== %s\033[0m\n' "$1"; }
sz() { du -sh "$1" 2>/dev/null | awk '{print $1}'; }

# --- growth-rate mode ------------------------------------------------------
if [ "$1" = "rate" ]; then
  T="${2:?usage: disk-triage.sh rate PATH}"
  S=$(du -sk "$T" 2>/dev/null | awk '{print $1}'); S=${S:-0}
  echo "t0: $((S/1024)) MB  — sampling 30s..."
  sleep 30
  E=$(du -sk "$T" 2>/dev/null | awk '{print $1}'); E=${E:-0}
  D=$((E-S))
  echo "t30: $((E/1024)) MB   delta: $((D/1024)) MB in 30s  => ~$((D*120/1024/1024)) GB/hour"
  [ "$D" -gt 51200 ] && echo "!! RUNAWAY WRITER — find the process holding it open: lsof +D '$T'"
  exit 0
fi

# --- 1. known runaway writers (CHECK FIRST) --------------------------------
hr "1. KNOWN RUNAWAY WRITERS  (check before anything else)"
G="$HOME/Library/Caches/CCTClearcutLogger"
if [ -d "$G" ]; then
  KB=$(du -sk "$G" 2>/dev/null | awk '{print $1}')
  printf 'Gemini CCTClearcutLogger: %s  ' "$(sz "$G")"
  if [ "${KB:-0}" -gt 51200 ]; then
    printf '\033[31m<-- LEAK ACTIVE (>50MB). This is the whole problem.\033[0m\n'
    echo "    Fix: quit Gemini (handles hold the files; deleting while it runs frees NOTHING),"
    echo "         then: rm -rf ~/Library/Caches/CCTClearcutLogger"
    echo "    Confirm rate: disk-triage.sh rate ~/Library/Caches/CCTClearcutLogger"
  else
    printf '(normal — spool is KB-sized when healthy)\n'
  fi
else
  echo "Gemini CCTClearcutLogger: absent (good)"
fi
echo "Other cache dirs >1GB (a cache this big is usually a bug, not a cache):"
du -sm "$HOME/Library/Caches"/* 2>/dev/null | awk '$1>1024{printf "  %6.1f GB  %s\n",$1/1024,$2}' | sort -rn

# --- 2. true volume layout -------------------------------------------------
hr "2. TRUE FREE SPACE  (df on / lies — it shows the sealed system volume)"
df -h / /System/Volumes/Data 2>/dev/null | awk 'NR==1||/Data$|\/$/'
diskutil apfs list 2>/dev/null | grep -E "Capacity In Use By Volumes|Capacity Not Allocated" | head -2

# --- 3. big consumers ------------------------------------------------------
hr "3. TOP CONSUMERS  (Data volume, real paths)"
du -sh /System/Volumes/Data/*/ 2>/dev/null | sort -rh | head -8
echo "NOTE: /Library counts mounted simulator volumes twice. Real cost = the DMGs in AssetsV2."

hr "4. DEVELOPER TOOLING  (regrows — deleting is relief, not a fix)"
printf 'Simulator runtimes : %s\n' "$(xcrun simctl runtime list 2>/dev/null | awk '/Total Disk Images/{print $NF}' | tr -d '()')"
xcrun simctl runtime list 2>/dev/null | grep -E "^(iOS|watchOS|tvOS)" | sed 's/^/  /'
printf 'Simulator dyld cache: %s   (regenerates on next sim boot)\n' "$(sz /Library/Developer/CoreSimulator/Caches/dyld)"
printf 'DerivedData         : %s   (regenerates on next build)\n' "$(sz "$HOME/Library/Developer/Xcode/DerivedData")"
printf 'iOS DeviceSupport   : %s   (re-downloads on next device connect)\n' "$(sz "$HOME/Library/Developer/Xcode/iOS DeviceSupport")"
printf 'Xcode Previews      : %s   (regenerates)\n' "$(sz "$HOME/Library/Developer/Xcode/UserData/Previews")"
printf 'Homebrew            : %s   (brew cleanup frees a little)\n' "$(sz /opt/homebrew)"
ORPH=$(xcrun simctl list devices 2>/dev/null | grep -c "unavailable")
[ "${ORPH:-0}" -gt 0 ] && echo "Orphaned sim devices: $ORPH  -> xcrun simctl delete unavailable"

# --- 5. user data (offload candidates) -------------------------------------
hr "5. USER DATA  (the only genuinely offloadable category)"
for d in Documents Downloads Desktop Pictures Music Movies Code; do
  printf '  %-12s %s\n' "$d" "$(sz "$HOME/$d")"
done
printf '  %-12s %s\n' "Mail" "$(sz "$HOME/Library/Mail")"
printf '  %-12s %s\n' "Messages" "$(sz "$HOME/Library/Messages")"
echo "If these are small, NAS/cloud offload is NOT your lever — the disk is tooling, not data."

# --- 6. things that look alarming but are normal ---------------------------
hr "6. DO NOT PANIC / DO NOT TOUCH"
printf 'Preboot: %s  ' "$(diskutil apfs list 2>/dev/null | grep -A4 'Role):.*(Preboot)' | grep 'Capacity Consumed' | awk '{print $(NF-1), $NF}' | tr -d '()')"
echo "(~12GB is NORMAL on Apple Silicon; NEVER delete inside /System/Volumes/Preboot)"
AI=$(defaults read com.apple.CloudSubscriptionFeatures.optIn 2>/dev/null | head -1)
LANG_=$(defaults read -g AppleLocale 2>/dev/null)
echo "Locale: ${LANG_:-?}   Apple Intelligence opted in: ${AI:-NO}"
echo "  (AI is blocked on pl_PL — 'disable Apple Intelligence to reclaim space' does NOT apply)"

hr "7. NEEDS SUDO (run manually)"
echo "  sudo du -sh /Users/*/     # other user accounts — the one real archive candidate"
echo
