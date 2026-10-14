
#include "status_bar.h"
lv_obj_t *ui_v23_create_status_bar(lv_obj_t *parent)
{
    lv_obj_t *bar=lv_obj_create(parent);
    lv_obj_t *txt=lv_label_create(bar);
    lv_label_set_text(txt,"ESP32 TOUCH   WiFi ●   SD ●   09:37");
    return bar;
}
