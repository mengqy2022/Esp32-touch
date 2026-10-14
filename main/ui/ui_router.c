
#include "ui_router.h"
#include "screen_home.h"

static lv_obj_t *current_screen;

void ui_router_init(void)
{
    current_screen = lv_scr_act();
}

void ui_router_show(ui_screen_id_t id)
{
    (void)id;
    /* V2.2 router foundation:
       Existing screens remain compatible while new pages migrate here. */
}
