#include "ui_widgets.h"
#include "ui_theme.h"

static void apply_card(lv_obj_t *o){
    const ui_theme_t *t=ui_theme_get();
    lv_obj_set_style_bg_color(o,t->panel,0);
    lv_obj_set_style_border_width(o,0,0);
    lv_obj_set_style_radius(o,t->radius,0);
}

lv_obj_t *ui_create_action_button(lv_obj_t *parent,const char *text,lv_event_cb_t cb,int id){
    lv_obj_t *b=lv_btn_create(parent);
    lv_obj_set_size(b,140,42);
    lv_obj_add_event_cb(b,cb,LV_EVENT_CLICKED,(void*)(intptr_t)id);
    lv_obj_set_style_radius(b,12,0);
    lv_obj_t *l=lv_label_create(b);
    lv_label_set_text(l,text);
    lv_obj_center(l);
    return b;
}

lv_obj_t *ui_create_status_bar(lv_obj_t *parent){
    lv_obj_t *bar=lv_obj_create(parent);
    lv_obj_set_size(bar,300,28);
    apply_card(bar);
    lv_obj_t *l=lv_label_create(bar);
    lv_label_set_text(l,"SYSTEM READY   |   TOUCH UI V2");
    lv_obj_center(l);
    return bar;
}
