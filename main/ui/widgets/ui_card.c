
#include "ui_card.h"
#include "../ui_theme_v22.h"

lv_obj_t *ui22_create_card(lv_obj_t *parent)
{
    lv_obj_t *card = lv_obj_create(parent);
    ui22_apply_card_style(card);
    return card;
}
