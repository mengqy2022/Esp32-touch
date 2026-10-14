
#include "home_dashboard.h"
#include "../widgets/glass_card.h"
#include "../widgets/status_bar.h"

lv_obj_t *ui_v23_create_home(void)
{
    lv_obj_t *scr=lv_obj_create(NULL);
    ui_v23_create_status_bar(scr);

    lv_obj_t *title=lv_label_create(scr);
    lv_label_set_text(title,"ESP32 TOUCH CENTER");

    ui_v23_create_card(scr,"CPU Monitor");
    ui_v23_create_card(scr,"Storage");
    ui_v23_create_card(scr,"Games");
    ui_v23_create_card(scr,"Settings");

    return scr;
}
