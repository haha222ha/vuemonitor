!macro customInstall
  DetailPrint "正在安装 XHS365..."
  SetOutPath "$INSTDIR"
  File /r "${BUILD_RESOURCES_DIR}\*"

  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\XHS365" \
    "DisplayName" "XHS365 - 小红书AI选品"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\XHS365" \
    "Publisher" "XHS365"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\XHS365" \
    "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\XHS365" \
    "UninstallString" "$INSTDIR\Uninstall XHS365.exe"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\XHS365" \
    "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\XHS365" \
    "NoRepair" 1
!macroend

!macro customUnInstall
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\XHS365"
  RMDir /r "$APPDATA\XHS365"
!macroend