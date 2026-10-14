#include "ui_theme.h"

static const ui_theme_t theme = {
    .bg = LV_COLOR_MAKE(0x0B,0x0F,0x14),
    .panel = LV_COLOR_MAKE(0x15,0x1B,0x23),
    .panel2 = LV_COLOR_MAKE(0x1D,0x26,0x32),
    .primary = LV_COLOR_MAKE(0x3B,0x82,0xF6),
    .accent = LV_COLOR_MAKE(0x22,0xC5,0x5E),
    .text = LV_COLOR_MAKE(0xF8,0xFA,0xFC),
    .text_dim = LV_COLOR_MAKE(0x94,0xA3,0xB8),
    .radius = 14,
    .padding = 12,
};

const ui_theme_t *ui_theme_get(void){ return &theme; }

void ui_theme_apply_screen(lv_obj_t *screen){
    const ui_theme_t *t=&theme;
    lv_obj_set_style_bg_color(screen,t->bg,0);
}

lv_obj_t *ui_create_card(lv_obj_t *parent){
    lv_obj_t *o=lv_obj_create(parent);
    lv_obj_set_style_bg_color(o,theme.panel,0);
    lv_obj_set_style_radius(o,theme.radius,0);
    lv_obj_set_style_pad_all(o,theme.padding,0);
    lv_obj_set_style_border_width(o,0,0);
    return o;
}

lv_obj_t *ui_create_title(lv_obj_t *parent,const char *text){
    lv_obj_t *l=lv_label_create(parent);
    lv_label_set_text(l,text);
    lv_obj_set_style_text_color(l,theme.text,0);
    lv_obj_set_style_text_font(l,&lv_font_montserrat_28,0);
    return l;
}
