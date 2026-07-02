local mp = require 'mp'

local anime4k_chain = '~~/shaders/Anime4K_v4.0/Anime4K_Restore_CNN_L.glsl:~~/shaders/Anime4K_v4.0/Anime4K_Upscale_CNN_x2_L.glsl'

local function toggle_anime4k()
    local current = mp.get_property('glsl-shaders', '')

    if current == anime4k_chain then
        mp.set_property('glsl-shaders', '')
        mp.osd_message('Anime4K: OFF')
    else
        mp.set_property('glsl-shaders', anime4k_chain)
        mp.osd_message('Anime4K: Restore CNN L + Upscale CNN x2 L')
    end
end

mp.add_key_binding('F5', 'toggle-anime4k', toggle_anime4k)
