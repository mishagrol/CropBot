from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
import aiogram.utils.markdown as md


inline_main_btns = [InlineKeyboardButton('Добавить поле', callback_data='main_add'),
                    InlineKeyboardButton('Выбрать поле', callback_data='main_edit')]

inline_main_kb = InlineKeyboardMarkup(one_time_keyboard=True)
inline_main_kb.add(*inline_main_btns)

inline_main_edit_kb = InlineKeyboardMarkup(one_time_keyboard=True).add(InlineKeyboardButton('Добавить поле', callback_data='main_add'))

inline_main_field_btns = [InlineKeyboardButton('Добавить полив', callback_data='mf_add_irrigation'),
                        InlineKeyboardButton('Добавить удобрения', callback_data='mf_add_npk'),
                        InlineKeyboardButton('Удалить полив', callback_data='mf_del_irrigation'),
                        InlineKeyboardButton('Удалить удобрения', callback_data='mf_del_npk'),
                        InlineKeyboardButton('Удалить поле', callback_data='mf_del_field'),
                        InlineKeyboardButton('Назад к выбору поля', callback_data='mf_back'),
                        InlineKeyboardButton('ПРОИЗВЕСТИ ВЫЧИСЛЕНИЯ', callback_data='mf_calc')
                        ]
inline_main_field_kb = InlineKeyboardMarkup(row_width=2, one_time_keyboard=True).add(*inline_main_field_btns)

def print_field_info(data):
    return  md.text(
                    'Конфигурация поля:',
                    md.text('Поле:', md.bold(data['name'])),
                    md.text('Координаты:', f"{data['latitude']}, {data['longitude']}"),
                    md.text('Культура:', md.bold(data['crop_name'])),
                    # md.text('Сорт:', md.bold(data['crop_full_name'])),
                    md.text('Посев:', data['crop_start']),
                    md.text('Сбор:', data['crop_end']),
                    md.text('Полив:'),
                    md.code('\n'.join([f"{irr_date} {float(irr_val): .2f}" for irr_date, irr_val in zip(data['irrigation_events'], data['irrigation_ammounts'])])).replace('\\', ''),
                    md.text('Удобрения: '),
                    md.code('\n'.join([f"{npk_date} {'/'.join(list(map(str, npk_val)))}" for npk_date, npk_val in zip(data['npk_events'], data['npk'])])).replace('\\', ''),
                    sep='\n',
                )

back_markup = ReplyKeyboardMarkup(resize_keyboard=True, selective=True, one_time_keyboard=True).add('Готово')

geo_example_text = md.text(
                    md.text("Отправьте геолокацию с точкой на поле или введите в формате широта, долгота, например:"),
                    md.code('46.306027, 39.311406').replace('\\', ''),
                    sep='\n',
                )
npk_format_text = md.text(
                    md.text("Введите дату внесения удобрений в формате 21.05, а затем конфигурацию NPK через /, например 10/40/50."),
                    md.text('Должно получиться ')+md.code('21.05 10/40/50').replace('\\', ''),
                    md.text('Можно ввести сразу несколько внесений удобрений через запятую:'),
                    md.code('21.05 10/40/50, 13.06 80/10/10, 17.08 20/30/10').replace('\\', ''),
                    md.text("Для отмены нажмите 'Готово'"),
                    sep='\n',
                )

irrigation_format_text = md.text(
                    md.text("Введите дату полива в формате 21.05, а затем количество воды в сантиметрах, например 10."),
                    md.text('Должно получиться ')+md.code('21.05 10').replace('\\', ''),
                    md.text('Можно ввести сразу несколько поливов через запятую:'),
                    md.code('21.05 10, 13.06 3.77, 17.08 4.88').replace('\\', ''),
                    md.text("Для отмены нажмите 'Готово'"),
                    sep='\n',
                )

def irrigations_added_text(irr_list):
    return md.text(
                    md.text("Добавлены поливы:"),
                    md.code('\n'.join([f"{irr_date.strftime('%Y-%m-%d')} {float(irr_val): .2f}" for irr_date, irr_val in irr_list])).replace('\\', ''),
                    md.text("Добавьте ещё или нажмите 'Готово'"),
                    sep='\n',
                )

def npks_added_text(npk_list):
    return md.text(
                    md.text("Добавлены внесения удобрений:"),
                    md.code('\n'.join([f"{npk_date.strftime('%Y-%m-%d')} {'/'.join(list(map(str, npk_val)))}" for npk_date, npk_val in npk_list])).replace('\\', ''),
                    md.text("Добавьте ещё или нажмите 'Готово'"),
                    sep='\n',
                )


### ENGLISH 


inline_main_btns_en = [InlineKeyboardButton('Add field', callback_data='main_add'),
                    InlineKeyboardButton('Select field', callback_data='main_edit')]

inline_main_kb_en = InlineKeyboardMarkup(one_time_keyboard=True)
inline_main_kb_en.add(*inline_main_btns_en)

inline_main_edit_kb_en = InlineKeyboardMarkup(one_time_keyboard=True).add(InlineKeyboardButton('Add field', callback_data='main_add'))

inline_main_field_btns_en = [InlineKeyboardButton('Add irrigation', callback_data='mf_add_irrigation'),
                        InlineKeyboardButton('Add fertilization', callback_data='mf_add_npk'),
                        InlineKeyboardButton('Remove irrigation', callback_data='mf_del_irrigation'),
                        InlineKeyboardButton('Remove fertilization', callback_data='mf_del_npk'),
                        InlineKeyboardButton('Remove field', callback_data='mf_del_field'),
                        InlineKeyboardButton('Back to select field', callback_data='mf_back'),
                        InlineKeyboardButton('COMPUTE', callback_data='mf_calc')
                        ]
inline_main_field_kb_en = InlineKeyboardMarkup(row_width=2, one_time_keyboard=True).add(*inline_main_field_btns_en)

def print_field_info_en(data):
    return  md.text(
                    'Field Configuration:',
                    md.text('Field:', md.bold(data['name'])),
                    md.text('Geolocation:', f"{data['latitude']}, {data['longitude']}"),
                    md.text('Crop:', md.bold(data['crop_name'])),
                    # md.text('Сорт:', md.bold(data['crop_full_name'])),
                    md.text('Sowing:', data['crop_start']),
                    md.text('Harwesting:', data['crop_end']),
                    md.text('Irrigation:'),
                    md.code('\n'.join([f"{irr_date} {float(irr_val): .2f}" for irr_date, irr_val in zip(data['irrigation_events'], data['irrigation_ammounts'])])).replace('\\', ''),
                    md.text('Fertilizers: '),
                    md.code('\n'.join([f"{npk_date} {'/'.join(list(map(str, npk_val)))}" for npk_date, npk_val in zip(data['npk_events'], data['npk'])])).replace('\\', ''),
                    sep='\n',
                )


back_markup_en = ReplyKeyboardMarkup(resize_keyboard=True, selective=True, one_time_keyboard=True).add('Done')

geo_example_text_en = md.text(
                    md.text("Send geolocation with a point in the field or enter in the format latitude, longitude, for example:"),
                    md.code('51.978, 5.634').replace('\\', ''),

                    
                    sep='\n',
                )
npk_format_text_en = md. text(
                    md.text("Enter the fertilization date in the format 21.05, and then the NPK configuration via /, for example 10/40/50."),
                    md.text('Should work ')+md.code('21.05 10/40/50').replace('\\',''),
                    md.text('You can enter several fertilizer applications at once, separated by commas:'),
                    md.code('21.05 10/40/50, 13.06 80/10/10, 17.08 20/30/10').replace('\\',''),
                    md.text("To cancel, click Done"),
                    sep='\n',
                    )

irrigation_format_text_en = md.text(
                md.text("Enter the irrigation date in the format 21.05, and then the amount of water in centimeters, for example 10."),
                md.text('Should work ')+md.code('21.05 10').replace('\\',''),
                md.text('You can enter multiple irrigations at once, separated by commas:'),
                md.code('21.05 10, 13.06 3.77, 17.08 4.88').replace('\\',''),
                md.text("To cancel, click 'Done'"),
                sep='\n',
                )

def irrigations_added_text_en(irr_list):
    return md.text(
                    md.text("Added irrigation events:"),
                    md.code('\n'.join([f"{irr_date.strftime('%Y-%m-%d')} {float(irr_val): .2f}" for irr_date, irr_val in irr_list])).replace('\\', ''),
                    md.text("Add more or click 'Done'"),
                    sep='\n',
                )

def npks_added_text_en(npk_list):
    return md.text(
                    md.text("Added fertilization events:"),
                    md.code('\n'.join([f"{npk_date.strftime('%Y-%m-%d')} {'/'.join(list(map(str, npk_val)))}" for npk_date, npk_val in npk_list])).replace('\\', ''),
                    md.text("Add more or click 'Done'"),
                    sep='\n',
                )
