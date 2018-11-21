
COMMAND_NAMES = {

    # Names of functions called from the command table. I believe these are just global DS1 engine functions.

    # Only seems to be used in menu files ([a-z]##-##.esd).
    0: ['DebugEvent'],
    
    # talk_param_id is used to look up both the FMG text ID and audio file ID.
    1: ['TalkToPlayer', 'talk_param_id', 'arg2', 'arg3'],
    
    2: ['InvokeEvent'],
    
    3: ['StopAttacking'],
    
    4: ['Attack'],
    
    5: ['RemoveMyAggro'],
    
    6: ['DisplayOneLineHelp'],
    
    7: ['TurnToFacePlayer'],
    
    8: ['ForceEndTalk'],
    
    9: ['ClearTalkProgressData'],
    
    10: ['ShowShopMessage'],
    
    # state = 0 (disable) or 1 (enable).
    11: ['SetEventState', 'event_flag_id', 'state'],
    
    12: ['CloseShopMessage'],
    
    13: ['OpenCampMenu'],
    
    14: ['CloseCampMenu'],
    
    15: ['ChangeTeamType'],
    
    16: ['SetDefaultTeamType'],
    
    # Not sure what first argument does.
    17: ['OpenGenericDialog', 'arg1', 'text_id', 'button_type', 'number_buttons', 'display_distance'],
    
    18: ['ForceCloseGenericDialog'],
    
    19: ['AddTalkListData'],
    
    20: ['ClearTalkListData'],
    
    21: ['RequestMoviePlayback'],
    
    22: ['OpenRegularShop'],
    
    23: ['OpenRepairShop'],
    
    24: ['OpenEnhanceShop'], # 0 = weapons, 10 = armor
    
    25: ['OpenHumanityMenu'],
    
    26: ['OpenMagicShop'],
    
    27: ['OpenMiracleShop'],
    
    28: ['OpenMagicEquip'],
    
    29: ['OpenMiracleEquip'],
    
    30: ['OpenRepository'],
    
    31: ['OpenSoul'],
    
    32: ['CloseMenu'],
    
    33: ['SetEventFlagRange'],
    
    34: ['OpenDepository'],
    
    35: ['ClearTalkActionState'],
    
    36: ['ClearTalkDisabledState'],
    
    37: ['SetTalkDisableStateMaxDuration'],
    
    38: ['SetUpdateDistance'],
    
    39: ['ClearPlayerDamageInfo'],
    
    40: ['OfferHumanity'],
    
    41: ['StartWarpMenuInit'],
    
    42: ['StartBonfireAnimLoop'],
    
    43: ['EndBonfireKindleAnimLoop'],
    
    44: ['OpenSellShop'],
    
    45: ['ChangePlayerStats'],
    
    46: ['OpenEquipmentChangeOfPurposeShop'],
    
    47: ['CombineMenuFlagAndEventFlag'],
    
    48: ['RequestSave'],
    
    49: ['ChangeMotionOffsetID'],
    
    50: ['PlayerEquipmentQuantityChange'],
    
    51: ['RequestUnlockTrophy'],
    
    52: ['EnterBonfireEventRange'],
    
    53: ['SetAquittalCostMessageTag'],
    
    54: ['SubtractAcquittalCostFromPlayerSouls'],
    
    55: ['ShuffleRNGSeed'],
    
    56: ['SetRNGSeed'],
    
    57: ['ReplaceTool'],
    
    58: ['BreakCovenantPledge'],
    
    59: ['PlayerRespawn'],
    
    60: ['GiveSpEffectToPlayer'],
    
    61: ['ShowGrandioseTextPresentation'],
    
    62: ['AddIzalithRankingPoints'],
    
    63: ['OpenItemAcquisitionMenu'],
    
    64: ['AcquireGesture'],
    
    65: ['ForceCloseMenu'],
    
    66: ['SetTalkTime'],
    
    67: ['CollectJustPyromancyFlame'],
    
    68: ['OpenArenaRanking'],

}
