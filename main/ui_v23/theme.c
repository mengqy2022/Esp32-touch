
#include "theme.h"
void ui_v23_apply_card(lv_obj_t *obj)
{
    lv_obj_set_style_radius(obj, UI_RADIUS, 0);
    lv_obj_set_style_bg_color(obj, lv_color_hex(UI_CARD_COLOR), 0);
    lv_obj_set_style_border_width(obj, 0, 0);
    lv_obj_set_style_pad_all(obj, 16, 0);
}
