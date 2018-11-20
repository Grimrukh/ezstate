
COMMAND_NAMES = {

    # Names of functions called from the command table. I believe these are just global DS1 engine functions.

    # No command.
    -1: ['(NULL)'],

    # Only seems to be used in menu files ([a-z]##-##.esd).
    0: ['StateDescription'],

    # talk_param_id is used to look up both the FMG text ID and audio file ID.
    1: ['PlayDialogue', 'talk_param_id', 'arg2', 'arg3'],

    # text_id = -1 disables the prompt.
    6: ['ShowActionPrompt', 'text_id'],

    # state = 0 (disable) or 1 (enable).
    11: ['SetEventFlag', 'event_flag_id', 'state'],

    # Not sure what first argument does.
    17: ['DisplayTextDialog', 'arg1', 'text_id', 'button_type', 'number_buttons', 'display_distance'],

    19: ['DisplayMenuItem', 'menu_index', 'item_name', 'required_flag'],

    22: ['AddShopLineup', 'param_start', 'param_end'],

    24: ['OpenReinforceMenu', 'menu_type'],  # 0 = weapons, 10 = armor

    49: ['AddAscensionMenu', 'required_flag', '?menu?'],

}
