
#pragma once
#include "lvgl.h"

#define UI22_RADIUS_CARD 18
#define UI22_RADIUS_BUTTON 12
#define UI22_PADDING 12

static inline void ui22_apply_card_style(lv_obj_t *obj)
{
    lv_obj_set_style_radius(obj, UI22_RADIUS_CARD, 0);
    lv_obj_set_style_pad_all(obj, UI22_PADDING, 0);
}
