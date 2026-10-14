
#include "glass_card.h"
#include "../theme.h"

lv_obj_t *ui_v23_create_card(lv_obj_t *parent,const char *title)
{
    lv_obj_t *card=lv_obj_create(parent);
    ui_v23_apply_card(card);
    lv_obj_t *label=lv_label_create(card);
    lv_label_set_text(label,title);
    return card;
}
