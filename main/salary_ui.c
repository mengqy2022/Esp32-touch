#include "salary_ui.h"
#include "salary_store.h"
#include "salary_cat_frames.h"
#include "net_utils.h"
#include "ui.h"
#include "ui_theme.h"
#include "ui_widgets.h"
#include "lvgl.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern const lv_font_t font_salary16;
extern const uint8_t cat_start[] asm("_binary_salary_cat_rle_start");
extern const uint8_t cat_end[] asm("_binary_salary_cat_rle_end");

static lv_obj_t *s_root, *s_image, *s_money, *s_caption, *s_detail, *s_state, *s_clock, *s_progress, *s_hint, *s_input;
static lv_timer_t *s_timer;
static uint8_t *s_pixels;
static lv_img_dsc_t s_descriptor;
static salary_config_t s_draft;
static int s_page, s_field, s_view, s_day = -1, s_frame;
static uint32_t s_frame_tick, s_second_tick;
static uint32_t s_edit_date;
static char s_number[20], s_notice[80];
static uint32_t s_built;
static volatile uint32_t s_rendered_frames;

uint32_t salary_ui_rendered_frames(void) { return s_rendered_frames; }

enum { INK = 0x080808, PANEL = 0x151515, LINE = 0x484848,
       ACCENT = 0xFFFFFF, TEXT = 0xEEEEEE, DIM = 0xB0B0B0 };

static lv_obj_t *panel(int x, int y, int width, int height)
{
    lv_obj_t *object = lv_obj_create(s_root);
    lv_obj_remove_style_all(object);
    lv_obj_set_pos(object, x, y);
    lv_obj_set_size(object, width, height);
    lv_obj_set_style_bg_opa(object, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(object, lv_color_hex(PANEL), 0);
    lv_obj_set_style_border_color(object, lv_color_hex(LINE), 0);
    lv_obj_set_style_border_width(object, 1, 0);
    lv_obj_set_style_radius(object, 8, 0);
    lv_obj_clear_flag(object, LV_OBJ_FLAG_SCROLLABLE);
    return object;
}

static void rebuild(void) { ui_draw_all(); }
static bool touch_ready(void) { return lv_tick_get() - s_built >= 180; }

static lv_obj_t *label(lv_obj_t *parent, const char *text, int x, int y, int width)
{
    lv_obj_t *object = lv_label_create(parent);
    lv_label_set_text(object, text);
    lv_obj_set_pos(object, x, y);
    lv_obj_set_width(object, width);
    lv_obj_set_style_text_font(object, &font_salary16, 0);
    lv_obj_set_style_text_color(object, lv_color_hex(TEXT), 0);
    lv_label_set_long_mode(object, LV_LABEL_LONG_WRAP);
    return object;
}

static lv_obj_t *button(lv_obj_t *parent, const char *text, int x, int y, int width, lv_event_cb_t callback, int id)
{
    lv_obj_t *object = ui_create_action_button(parent, text, callback, id);
    lv_obj_set_pos(object, x, y);
    lv_obj_set_size(object, width, 34);
    lv_obj_set_style_pad_all(object, 2, 0);
    lv_obj_set_style_bg_color(object, lv_color_hex(PANEL), 0);
    lv_obj_set_style_border_width(object, 1, 0);
    lv_obj_set_style_border_color(object, lv_color_hex(LINE), 0);
    lv_obj_set_style_radius(object, 6, 0);
    lv_obj_set_style_text_color(object, lv_color_hex(ACCENT), 0);
    lv_obj_set_style_bg_color(object, lv_color_hex(LINE), LV_STATE_PRESSED);
    lv_obj_set_style_shadow_width(object, 0, 0);
    lv_obj_set_style_text_font(object, &font_salary16, 0);
    return object;
}

static void cleanup(void)
{
    if (s_timer) { lv_timer_del(s_timer); s_timer = NULL; }
    if (s_root) { lv_obj_del(s_root); s_root = NULL; }
    if (s_pixels) {
        lv_img_cache_invalidate_src(&s_descriptor);
        free(s_pixels);
        s_pixels = NULL;
    }
    s_image = NULL;
    s_day = -1;
}

void salary_ui_leave(void)
{
    cleanup();
    s_page = 0;
    s_notice[0] = 0;
}

static void on_back(lv_event_t *event)
{
    (void)event;
    if (!touch_ready()) return;
    if (!s_page) ui_set_screen(SCREEN_OTHER_MENU);
    else { s_page = s_page == 4 ? 3 : s_page == 1 ? 0 : 1; s_notice[0] = 0; rebuild(); }
}

static void on_settings(lv_event_t *event)
{
    (void)event;
    if (!touch_ready()) return;
    salary_data_t data;
    salary_store_snapshot(&data);
    s_draft = data.config;
    s_page = 1;
    s_notice[0] = 0;
    rebuild();
}

static void on_view(lv_event_t *event)
{
    (void)event;
    if (touch_ready()) { s_view = (s_view + 1) % 3; s_second_tick = 0; }
}

static void show_number(int field)
{
    s_field = field;
    if (!field) snprintf(s_number, sizeof(s_number), "%"PRIu32".%02"PRIu32, s_draft.monthly_fen / 100, s_draft.monthly_fen % 100);
    else if (field <= 4) snprintf(s_number, sizeof(s_number), "%02u%02u", s_draft.times[field - 1] / 60, s_draft.times[field - 1] % 60);
    else snprintf(s_number, sizeof(s_number), "%08"PRIu32, s_edit_date);
    s_page = field == 5 ? 4 : 2;
    s_notice[0] = 0;
    rebuild();
}

static void on_edit(lv_event_t *event)
{
    if (!touch_ready()) return;
    int id = (int)(intptr_t)lv_event_get_user_data(event);
    if (id <= 4) show_number(id);
    else if (id == 5) { s_page = 5; rebuild(); }
    else if (id == 6) { s_draft.use_calendar = !s_draft.use_calendar; rebuild(); }
    else if (id == 7) {
        time_t now = time(NULL);
        struct tm local;
        localtime_r(&now, &local);
        s_edit_date = net_time_synced() ? (local.tm_year + 1900) * 10000 + (local.tm_mon + 1) * 100 + local.tm_mday : 20261020;
        s_page = 3; rebuild();
    } else if (id == 8) { s_draft.boot_cat = !s_draft.boot_cat; rebuild(); }
    else if (id == 9) {
        if (!salary_config_valid(&s_draft)) snprintf(s_notice, sizeof(s_notice), "时间需依次递增，至少选一个工作日");
        else {
            esp_err_t error = salary_store_config(&s_draft);
            if (error == ESP_OK) { s_page = 0; s_notice[0] = 0; }
            else snprintf(s_notice, sizeof(s_notice), "保存失败，原设置保留");
        }
        rebuild();
    }
}

static bool accept_number(void)
{
    size_t length = strlen(s_number);
    if (!length) return false;
    if (s_field == 0) {
        uint64_t yuan = 0;
        size_t i = 0;
        while (i < length && s_number[i] != '.') {
            if (s_number[i] < '0' || s_number[i] > '9') return false;
            yuan = yuan * 10 + s_number[i++] - '0';
            if (yuan > SALARY_MAX_FEN / 100) return false;
        }
        unsigned fraction = 0, digits = 0;
        if (i < length) {
            ++i;
            while (i < length) {
                if (s_number[i] < '0' || s_number[i] > '9' || ++digits > 2) return false;
                fraction = fraction * 10 + s_number[i++] - '0';
            }
        }
        if (digits == 1) fraction *= 10;
        if (yuan * 100 + fraction > SALARY_MAX_FEN) return false;
        s_draft.monthly_fen = yuan * 100 + fraction;
    } else {
        for (size_t i = 0; i < length; ++i) if (s_number[i] < '0' || s_number[i] > '9') return false;
        unsigned long value = strtoul(s_number, NULL, 10);
        if (s_field == 5) {
            if (length != 8 || !salary_date_valid(value)) return false;
            s_edit_date = value;
        } else {
            if (length != 4 || value / 100 > 23 || value % 100 > 59) return false;
            s_draft.times[s_field - 1] = value / 100 * 60 + value % 100;
        }
    }
    return true;
}

static void on_number(lv_event_t *event)
{
    if (!touch_ready()) return;
    lv_obj_t *keys = lv_event_get_target(event);
    uint16_t key = lv_btnmatrix_get_selected_btn(keys);
    const char *text = lv_btnmatrix_get_btn_text(keys, key);
    if (!text) return;
    size_t length = strlen(s_number);
    if (!strcmp(text, "DEL")) { if (length) s_number[length - 1] = 0; }
    else if (!strcmp(text, "OK")) {
        if (accept_number()) { s_page = s_field == 5 ? 3 : 1; s_notice[0] = 0; rebuild(); return; }
        snprintf(s_notice, sizeof(s_notice), "格式错误，请检查金额或日期时间");
    } else if (length < (s_field == 0 ? 10u : s_field == 5 ? 8u : 4u)) {
        s_number[length] = *text; s_number[length + 1] = 0;
    }
    lv_label_set_text(s_input, s_number[0] ? s_number : "_");
    lv_label_set_text(s_hint, s_notice);
}

static void on_weekday(lv_event_t *event)
{
    if (!touch_ready()) return;
    int day = (int)(intptr_t)lv_event_get_user_data(event);
    s_draft.weekdays ^= 1u << day;
    rebuild();
}

static void on_date(lv_event_t *event)
{
    if (!touch_ready()) return;
    int mode = (int)(intptr_t)lv_event_get_user_data(event);
    if (mode == 2) { show_number(5); return; }
    esp_err_t error = salary_store_override(s_edit_date, mode);
    snprintf(s_notice, sizeof(s_notice), "%s", error == ESP_OK ? "日期设置已保存" : "保存失败：日期无效或已满32条");
    rebuild();
}

static bool draw_frame(unsigned frame)
{
    const salary_cat_frame_t *info = &salary_cat_frames[frame];
    if (info->offset + info->length > (size_t)(cat_end - cat_start) || info->length % 2) return false;
    const uint8_t *source = cat_start + info->offset;
    size_t decoded = 0;
    for (unsigned i = 0; i < info->length; i += 2) {
        unsigned count = source[i];
        if (!count || decoded + count > 112 * 112) return false;
        memset(s_pixels + 1024 + decoded, source[i + 1], count);
        decoded += count;
    }
    if (decoded != 112 * 112) return false;
    lv_img_cache_invalidate_src(&s_descriptor);
    lv_obj_invalidate(s_image);
    ++s_rendered_frames;
    return true;
}

static void format_money(char *text, size_t size, int64_t fen)
{
    snprintf(text, size, "%"PRId64".%02"PRId64, fen / 100, fen % 100);
}

static void timer(lv_timer_t *unused)
{
    (void)unused;
    uint32_t tick = lv_tick_get();
    bool synced = net_time_synced();
    time_t now = time(NULL);
    struct tm local;
    localtime_r(&now, &local);
    salary_data_t data;
    salary_store_snapshot(&data);
    salary_result_t result;
    bool valid = synced && salary_calculate(&data, &local, &result);
    int day = valid ? (local.tm_wday + 6) % 7 : 0;
    int animation = valid ? salary_cat_index(&data, local.tm_year + 1900, local.tm_mon + 1, local.tm_mday) : 0;
    if (s_pixels && (s_day != animation || tick - s_frame_tick >= salary_cat_frames[s_frame].duration)) {
        if (s_day != animation) { s_day = animation; s_frame = salary_cat_ranges[animation][0]; }
        else {
            ++s_frame;
            if (s_frame >= salary_cat_ranges[animation][0] + salary_cat_ranges[animation][1]) s_frame = salary_cat_ranges[animation][0];
        }
        draw_frame(s_frame);
        s_frame_tick = tick;
    }
    if (s_second_tick && tick - s_second_tick < 1000) return;
    s_second_tick = tick;
    if (!valid) {
        lv_label_set_text(s_clock, "等待电脑或 Wi-Fi 校时");
        lv_label_set_text(s_money, "--.--");
        lv_label_set_text(s_state, "时间未校准，暂不计算");
        lv_label_set_text(s_detail, "按排班估算，非考勤记录");
        lv_label_set_text(s_hint, "请连接 Dashboard 或 Wi-Fi");
        lv_bar_set_value(s_progress, 0, LV_ANIM_OFF);
        return;
    }
    static const char *week[] = {"周一", "周二", "周三", "周四", "周五", "周六", "周日"};
    char text[160];
    snprintf(text, sizeof(text), "%02d-%02d %s %02d:%02d", local.tm_mon + 1, local.tm_mday, week[day], local.tm_hour, local.tm_min);
    lv_label_set_text(s_clock, text);
    const char *captions[] = {"今日已赚 / CNY", "本月估算 / CNY", "年薪估算 / CNY"};
    lv_label_set_text(s_caption, captions[s_view]);
    format_money(text, sizeof(text), s_view == 0 ? result.today_fen : s_view == 1 ? result.month_fen : result.annual_fen);
    lv_label_set_text(s_money, text);
    lv_obj_set_style_text_font(s_money, strlen(text) > 9 ? &lv_font_montserrat_16 : &lv_font_montserrat_28, 0);
    snprintf(text, sizeof(text), "今日 %02d:%02d:%02d\n本月 %d 个工作日", result.worked_seconds / 3600,
             result.worked_seconds / 60 % 60, result.worked_seconds % 60, result.workdays);
    lv_label_set_text(s_detail, text);
    const char *states[] = {"距离上班", "距离午休", "午休 · 距离上班", "距离下班", "今日工作已完成", "今日休息"};
    if (result.countdown) snprintf(text, sizeof(text), "%s %02d:%02d:%02d", states[result.phase], result.countdown / 3600,
                                  result.countdown / 60 % 60, result.countdown % 60);
    else snprintf(text, sizeof(text), "%s", states[result.phase]);
    lv_label_set_text(s_state, text);
    lv_bar_set_value(s_progress, result.worked_seconds * 100 / result.daily_seconds, LV_ANIM_OFF);
    uint32_t today = (local.tm_year + 1900) * 10000 + (local.tm_mon + 1) * 100 + local.tm_mday;
    int manual = -1;
    for (int i = 0; i < SALARY_OVERRIDES; ++i)
        if (data.overrides[i].date == today) manual = data.overrides[i].work;
    if (manual >= 0) snprintf(text, sizeof(text), "%s · 日期例外优先", manual ? "手动指定上班" : "手动指定休息");
    else if (day >= 5 && result.workday && data.config.use_calendar && result.calendar_known)
        snprintf(text, sizeof(text), "调休上班 · 中国日历 %u", data.calendar.year);
    else if (data.config.use_calendar && !result.calendar_known) snprintf(text, sizeof(text), "调休日历未覆盖本月，按每周排班");
    else if (data.config.use_calendar) snprintf(text, sizeof(text), "中国调休 %u · 周末上班支持", data.calendar.year);
    else snprintf(text, sizeof(text), "按每周排班 · 日期例外优先");
    lv_label_set_text(s_hint, text);
}

void salary_ui_build(void)
{
    cleanup();
    lv_obj_clean(lv_scr_act());
    s_root = lv_obj_create(lv_scr_act());
    lv_obj_remove_style_all(s_root);
    lv_obj_set_size(s_root, 320, 240);
    lv_obj_set_style_bg_opa(s_root, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(s_root, lv_color_hex(INK), 0);
    lv_obj_clear_flag(s_root, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_t *title = label(s_root, s_page ? "月薪猫 / 设置" : "SALARY CAT", 10, 10, 172);
    lv_obj_set_style_text_color(title, lv_color_hex(ACCENT), 0);
    lv_obj_t *rule = panel(8, 36, 304, 1);
    lv_obj_set_style_bg_color(rule, lv_color_hex(LINE), 0);
    button(s_root, "返回", 258, 3, 56, on_back, 0);
    s_built = lv_tick_get();
    if (s_page == 1) {
        lv_obj_t *list = lv_obj_create(s_root);
        lv_obj_set_pos(list, 4, 43); lv_obj_set_size(list, 312, 145);
        lv_obj_set_style_pad_all(list, 3, 0);
        lv_obj_set_style_bg_color(list, lv_color_hex(INK), 0);
        lv_obj_set_style_border_width(list, 0, 0);
        lv_obj_set_style_bg_color(list, lv_color_hex(DIM), LV_PART_SCROLLBAR);
        char text[80];
        snprintf(text, sizeof(text), "月薪 %"PRIu32".%02"PRIu32" 元", s_draft.monthly_fen / 100, s_draft.monthly_fen % 100);
        button(list, text, 0, 0, 290, on_edit, 0);
        const char *names[] = {"上午上班", "上午下班", "下午上班", "下午下班"};
        for (int i = 0; i < 4; ++i) {
            snprintf(text, sizeof(text), "%s %02u:%02u", names[i], s_draft.times[i] / 60, s_draft.times[i] % 60);
            button(list, text, 0, (i + 1) * 39, 290, on_edit, i + 1);
        }
        button(list, "设置每周工作日", 0, 195, 290, on_edit, 5);
        button(list, s_draft.use_calendar ? "中国调休：开启" : "中国调休：关闭", 0, 234, 290, on_edit, 6);
        button(list, "指定日期上班 / 休息", 0, 273, 290, on_edit, 7);
        button(list, s_draft.boot_cat ? "开机页面：月薪猫" : "开机页面：原主页", 0, 312, 290, on_edit, 8);
        label(s_root, s_notice[0] ? s_notice : "上下滑动设置，保存后生效", 8, 191, 220);
        button(s_root, "保存", 244, 199, 70, on_edit, 9);
    } else if (s_page == 2 || s_page == 4) {
        label(s_root, s_field == 0 ? "月薪金额，最多两位小数" : s_field == 5 ? "日期格式：YYYYMMDD" : "时间格式：HHMM，如 0900", 8, 43, 304);
        s_input = label(s_root, s_number, 8, 64, 304);
        lv_obj_set_style_text_font(s_input, &lv_font_montserrat_28, 0);
        lv_obj_t *keys = lv_btnmatrix_create(s_root);
        lv_obj_set_style_bg_color(keys, lv_color_hex(INK), 0);
        lv_obj_set_style_border_width(keys, 0, 0);
        lv_obj_set_style_bg_color(keys, lv_color_hex(PANEL), LV_PART_ITEMS);
        lv_obj_set_style_text_color(keys, lv_color_hex(ACCENT), LV_PART_ITEMS);
        lv_obj_set_style_shadow_width(keys, 0, LV_PART_ITEMS);
        lv_obj_set_style_bg_color(keys, lv_color_hex(LINE), LV_PART_ITEMS | LV_STATE_PRESSED);
        static const char *map[] = {"1","2","3","DEL","\n","4","5","6",".","\n","7","8","9","OK","\n","0",""};
        lv_btnmatrix_set_map(keys, map);
        lv_obj_set_pos(keys, 4, 97); lv_obj_set_size(keys, 312, 118);
        lv_obj_add_event_cb(keys, on_number, LV_EVENT_VALUE_CHANGED, NULL);
        s_hint = label(s_root, s_notice, 6, 218, 308);
    } else if (s_page == 3) {
        char text[80];
        snprintf(text, sizeof(text), "%04"PRIu32"-%02"PRIu32"-%02"PRIu32, s_edit_date / 10000, s_edit_date / 100 % 100, s_edit_date % 100);
        button(s_root, text, 8, 45, 304, on_date, 2);
        salary_data_t data; salary_store_snapshot(&data);
        const char *mode = "自动规则";
        for (int i = 0; i < SALARY_OVERRIDES; ++i) if (data.overrides[i].date == s_edit_date)
            mode = data.overrides[i].work ? "手动：上班" : "手动：休息";
        label(s_root, mode, 8, 87, 300);
        button(s_root, "上班", 8, 118, 96, on_date, 1);
        button(s_root, "休息", 112, 118, 96, on_date, 0);
        button(s_root, "自动", 216, 118, 96, on_date, -1);
        label(s_root, s_notice[0] ? s_notice : "日期设置立即保存，自动可删除覆盖\n最多保存32个例外日期", 8, 168, 300);
    } else if (s_page == 5) {
        static const char *names[] = {"周一", "周二", "周三", "周四", "周五", "周六", "周日"};
        for (int i = 0; i < 7; ++i) {
            lv_obj_t *item = button(s_root, names[i], 8 + i % 3 * 104, 49 + i / 3 * 43, 96, on_weekday, i);
            bool selected = (s_draft.weekdays & (1u << i)) != 0;
            lv_obj_set_style_bg_color(item, lv_color_hex(selected ? LINE : PANEL), 0);
            lv_obj_set_style_border_color(item, lv_color_hex(selected ? ACCENT : LINE), 0);
        }
        label(s_root, "高亮为工作日，返回后点保存\n手动日期及开启的调休表优先", 8, 186, 304);
    } else {
        button(s_root, "设置", 196, 3, 56, on_settings, 0);
        s_clock = label(s_root, "等待校时", 10, 40, 304);
        lv_obj_set_style_text_color(s_clock, lv_color_hex(DIM), 0);
        panel(8, 62, 120, 118);
        panel(136, 62, 176, 118);
        s_pixels = calloc(1024 + 112 * 112, 1);
        if (s_pixels) {
            lv_color32_t *palette = (lv_color32_t *)s_pixels;
            for (unsigned i = 0; i < 256; ++i) {
                unsigned red = ((i >> 5) & 7) * 255 / 7;
                unsigned green = ((i >> 2) & 7) * 255 / 7;
                unsigned blue = (i & 3) * 255 / 3;
                uint8_t gray = (red * 77 + green * 150 + blue * 29 + 128) >> 8;
                palette[i].ch.red = palette[i].ch.green = palette[i].ch.blue = gray;
                palette[i].ch.alpha = i ? 255 : 0;
            }
            s_descriptor = (lv_img_dsc_t){.header = {.cf = LV_IMG_CF_INDEXED_8BIT, .w = 112, .h = 112},
                .data_size = 1024 + 112 * 112, .data = s_pixels};
            s_image = lv_img_create(s_root); lv_img_set_src(s_image, &s_descriptor);
            lv_obj_set_pos(s_image, 12, 65);
        } else label(s_root, "猫咪暂不可用\n内存不足", 8, 85, 112);
        s_caption = label(s_root, "今日已赚 / CNY", 144, 70, 160);
        lv_obj_set_style_text_color(s_caption, lv_color_hex(DIM), 0);
        s_money = label(s_root, "--.--", 144, 96, 160);
        lv_obj_set_style_text_font(s_money, &lv_font_montserrat_28, 0);
        lv_obj_set_style_text_color(s_money, lv_color_hex(ACCENT), 0);
        lv_obj_add_flag(s_money, LV_OBJ_FLAG_CLICKABLE);
        lv_obj_add_event_cb(s_money, on_view, LV_EVENT_CLICKED, NULL);
        s_detail = label(s_root, "按排班估算", 144, 133, 160);
        lv_obj_set_style_text_color(s_detail, lv_color_hex(DIM), 0);
        s_state = label(s_root, "等待校时", 10, 187, 302);
        lv_obj_set_style_text_color(s_state, lv_color_hex(TEXT), 0);
        s_progress = lv_bar_create(s_root); lv_obj_set_pos(s_progress, 10, 212); lv_obj_set_size(s_progress, 300, 4);
        lv_obj_set_style_bg_color(s_progress, lv_color_hex(LINE), 0);
        lv_obj_set_style_bg_color(s_progress, lv_color_hex(ACCENT), LV_PART_INDICATOR);
        s_hint = label(s_root, "点击金额切换今日 / 本月 / 年薪", 10, 220, 302);
        lv_obj_set_style_text_color(s_hint, lv_color_hex(DIM), 0);
        s_second_tick = 0; s_frame_tick = 0;
        timer(NULL);
        s_timer = lv_timer_create(timer, 70, NULL);
    }
}
