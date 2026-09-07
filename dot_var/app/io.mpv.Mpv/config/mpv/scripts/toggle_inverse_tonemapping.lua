local mp = require 'mp'

local function is_true(prop)
    local v = mp.get_property_native(prop)
    return v == true or v == 'yes' or v == '1'
end

local function set_bool(prop, val)
    mp.set_property_native(prop, val)
end

local function toggle_mapping()
    if is_true('inverse-tone-mapping') then
        set_bool('inverse-tone-mapping', false)
        -- set_bool('target-colorspace-hint', false)
        mp.osd_message('SDR→HDR mapping: OFF')
    else
        set_bool('inverse-tone-mapping', true)
        -- set_bool('target-colorspace-hint', true)
        mp.osd_message('SDR→HDR mapping: ON')
    end
end

mp.add_key_binding('F4', 'toggle-inverse-tone-mapping', toggle_mapping)
