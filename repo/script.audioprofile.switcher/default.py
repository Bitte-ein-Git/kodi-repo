import xbmc
import xbmcaddon
import xbmcgui

addon = xbmcaddon.Addon()
addon_name = addon.getAddonInfo('name')

def main():
    active_profiles = []

    for i in range(1, 11):
        is_enabled = addon.getSettingBool(f"profile_{i}_enabled")
        
        if is_enabled:
            custom_name = addon.getSetting(f"profile_{i}_name").strip()
            
            display_name = custom_name if custom_name else f"Profile {i}"
            
            active_profiles.append({
                'id': i,
                'name': display_name
            })

    if not active_profiles:
        dialog = xbmcgui.Dialog()
        dialog.notification(addon_name, 'Kein Profil aktiviert! Bitte konfigurieren.', xbmcgui.NOTIFICATION_ERROR, 5000)
        addon.openSettings()
        return

    options = [profile['name'] for profile in active_profiles]

    dialog = xbmcgui.Dialog()
    selected_index = dialog.select('Switch Audio Profile', options)

    if selected_index >= 0:
        selected_profile_id = active_profiles[selected_index]['id']
        
        xbmc.executebuiltin(f"RunScript(script.audio.profiles,{selected_profile_id})")[span_1](start_span)[span_1](end_span)
        xbmc.log(f"[{addon_name}] Switched to profile ID {selected_profile_id} ({active_profiles[selected_index]['name']})", level=xbmc.LOGINFO)

if __name__ == '__main__':
    main()