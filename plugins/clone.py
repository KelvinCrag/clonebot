# ----------------------------------- https://github.com/m4mallu/clonebot ---------------------------------------------#
import time
import pytz
import asyncio
from bot import Bot
from math import trunc
from library.sql import *
from presets import Presets
from datetime import datetime
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from library.buttons import reply_markup_stop, reply_markup_finished, reply_markup_resume
from library.chat_support import calc_percentage, calc_progress, save_target_cfg, set_to_defaults, date_time_calc
#
bot_start_time = time.time()
#
async def clone_medias(bot: Bot, m: Message):
    try:
        id = int(m.chat.id)
        query = await query_msg(id)
        clone_cancel_key[id] = int(m.id)
        #
        start_time = time.time()
        start_date = datetime.today().strftime("%d/%m/%y")
        clone_start_time = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%I:%M %p')
        #
        file_name = caption = report = str()
        #
        delay = limit = doc = video = audio = text = voice = photo = total_copied = matching = msg_id = int()
        #
        # Create mandatory variables from the database query
        source_chat = int(query.s_chat)
        target_chat = int(query.d_chat)
        start_id = int(query.from_id)
        end_id = int(query.to_id)
        end_msg_id = int(query.last_msg_id)
        #
        clone_delay = bool(query.delayed_clone)
        default_caption = bool(query.caption)
        fn_caption = bool(query.file_caption)
        #
        # Define the clone delay
        if bool(clone_delay):
            delay = 10
        else:
            delay = 3
        #
        # The values will be switched if the start message id is greater than the end message id
        if start_id > end_id:
            start_id = start_id ^ end_id
            end_id = end_id ^ start_id
            start_id = start_id ^ end_id
        else:
            pass
        #
        # Creating variables for progress bar and the percentage calculation
        if not bool(start_id):
            sp = 0
        else:
            sp = start_id
        if not bool(end_id):
            ep = end_msg_id
        else:
            ep = end_id
        #
        # Validate/Warm-up Peer Cache
        # This prevents "ValueError: Peer id invalid" by refreshing the dialog list if a chat is unknown
        for chat_to_resolve in [source_chat, target_chat]:
            if not chat_to_resolve:
                continue
            try:
                await bot.USER.get_chat(chat_to_resolve)
            except Exception:
                # If get_chat fails, iterate dialogs to refresh Pyrogram's internal peer cache
                async for dialog in bot.USER.get_dialogs():
                    if dialog.chat.id == chat_to_resolve:
                        break
        #
        await m.edit_text(Presets.INITIAL_MESSAGE_TEXT)
        await asyncio.sleep(1)
        msg = await m.reply_text(Presets.WAIT_MSG, reply_markup=reply_markup_stop)
        #
        for offset in reversed(
                range(end_id+1, (1 if not bool(start_id) else start_id)-1, (start_id - 1) if not bool(start_id) else -1)):
            async for user_message in bot.USER.get_chat_history(chat_id=source_chat, offset_id=offset, limit=1):
                if not user_message.empty:
                    messages = await bot.USER.get_messages(source_chat, user_message.id, replies=0)
                    msg_id = messages.id
                    cur_time = time.time()
                    cur_date = datetime.today().strftime("%d/%m/%y")
                    days, hours = await date_time_calc(start_date, start_time, cur_date, cur_time)
                    #
                    while id in clone_pause_key:
                        if id not in clone_cancel_key:
                            await save_target_cfg(id, target_chat)
                            if not int(total_copied):
                                await m.delete()
                            await asyncio.sleep(2)
                            await msg.edit(Presets.CANCELLED_MSG, reply_markup=reply_markup_finished)
                            await bot.USER.send_message("me", report, disable_web_page_preview=True)
                            await set_to_defaults(id)
                            await set_to_defaults(id)
                            clone_cancel_key.pop(id, None)
                            clone_pause_key.pop(id, None)
                            return
                        await asyncio.sleep(1)
                    #
                    report = Presets.CLONE_REPORT.format(time.strftime("%I:%M %p"), source_chat, target_chat,
                                                         "1" if not bool(start_id) else start_id,
                                                         end_msg_id if not bool(msg_id) else msg_id,
                                                         "🟡" if bool(clone_delay) else "🚫",
                                                         "🟡" if bool(default_caption) else "🚫",
                                                         "🟡" if bool(fn_caption) else "🚫",
                                                         int(total_copied), doc, video, audio, photo, voice, text, matching)
                    # If the user cancelled the clone operation
                    if id not in clone_cancel_key:
                        await save_target_cfg(id, target_chat)
                        if not int(total_copied):
                            await m.delete()
                        await asyncio.sleep(2)
                        await msg.edit(Presets.CANCELLED_MSG, reply_markup=reply_markup_finished)
                        await bot.USER.send_message("me", report, disable_web_page_preview=True)
                        await set_to_defaults(id)
                        await set_to_defaults(id)
                        clone_cancel_key.pop(id, None)
                        return
                    else:
                        pass
                    for file_type in file_types:
                        media = getattr(messages, file_type, None)
                        if media is not None:
                            uid = str(media.file_unique_id) if hasattr(media, 'file_unique_id') else None
                            
                            # Extract Filename Logic
                            file_name = str()
                            if file_type == 'document': file_name = messages.document.file_name
                            elif file_type == 'video': file_name = messages.video.file_name
                            elif file_type == 'audio': file_name = messages.audio.file_name
                            elif file_type == "voice": file_name = messages.caption
                            elif file_type == "photo": file_name = messages.caption
                            elif file_type == "text": file_name = str()
                            
                            if not file_name:
                                file_name = getattr(messages, "caption", str()) or str()

                            if len(file_name) > 60:
                                file_name = file_name[:57] + "..."

                            is_duplicate = False
                            # Duplicate Check
                            if (uid is not None) and (uid in master_index):
                                matching += 1
                                is_duplicate = True
                            else:
                                if uid is not None:
                                    master_index.append(uid)
                                # Increment counters
                                if file_type == 'document': doc += 1
                                elif file_type == 'video': video += 1
                                elif file_type == 'audio': audio += 1
                                elif file_type == "voice": voice += 1
                                elif file_type == "photo": photo += 1
                                elif file_type == "text": text += 1

                            # Status Update (Common)
                            total_copied = doc + video + audio + voice + photo + text
                            pct = await calc_percentage(sp, ep, msg_id)
                            update_time = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%I:%M %p')
                            try:
                                await m.edit(
                                    Presets.MESSAGE_COUNT.format(
                                        int(msg_id),
                                        int(total_copied),
                                        trunc(pct) if pct <= 100 else "- ",
                                        days,
                                        hours,
                                        clone_start_time,
                                        update_time,
                                        matching,
                                        file_name
                                    ),
                                    parse_mode=ParseMode.HTML,
                                    disable_web_page_preview=True
                                )
                            except FloodWait as e:
                                await asyncio.sleep(e.value)
                            except Exception:
                                pass
                            
                            # Progress Bar Update (Common)
                            progress = await calc_progress(pct)
                            try:
                                if id in clone_pause_key:
                                    reply_markup = reply_markup_resume
                                else:
                                    reply_markup = reply_markup_stop
                                await msg.edit("🇮🇳 | " + progress if pct <= 100 else Presets.BLOCK,
                                               reply_markup=reply_markup)
                            except Exception:
                                pass
                            
                            # Copy Action (Only if not duplicate)
                            if not is_duplicate:
                                # Caption Logic
                                if (file_type != "text") and (id in custom_caption):
                                    caption = custom_caption[id]
                                elif bool(default_caption):
                                    caption = messages.caption
                                elif bool(fn_caption):
                                    try:
                                        caption = str(file_name).rsplit('.', 1)[0]
                                    except Exception:
                                        caption = str()
                                else:
                                    caption = str()

                                try:
                                    await bot.USER.copy_message(
                                        chat_id=target_chat,
                                        from_chat_id=source_chat,
                                        caption=caption if bool(caption) else str(),
                                        message_id=msg_id,
                                        reply_markup=messages.reply_markup,
                                        disable_notification=True
                                    )
                                except FloodWait as e:
                                    await asyncio.sleep(e.value)
                                except Exception:
                                    await msg.edit_text(Presets.COPY_ERROR, reply_markup=reply_markup_finished)
                                    await bot.USER.send_message("me", report, disable_web_page_preview=True)
                                    await set_to_defaults(id)
                                    if not int(total_copied):
                                        await m.delete()
                                    if not int(total_copied):
                                        await m.delete()
                                    clone_cancel_key.pop(id, None)
                                    return

                                await asyncio.sleep(delay)

                                # Termination Check
                                if end_id and (int(msg_id) >= end_id):
                                    if not int(total_copied):
                                        await m.delete()
                                    await msg.edit(Presets.FINISHED_TEXT, reply_markup=reply_markup_finished)
                                    await bot.USER.send_message("me", report, disable_web_page_preview=True)
                                    await set_to_defaults(id)
                                    await set_to_defaults(id)
                                    clone_cancel_key.pop(id, None)
                                    return
                        else:
                            pass
                else:
                    pass
    
        # If the clone operation is automatically completed by the bot
        await save_target_cfg(id, target_chat)
        if not int(total_copied):
            await m.delete()
        await m.edit_reply_markup(None)
        await msg.edit(Presets.FINISHED_TEXT, reply_markup=reply_markup_finished)
        await bot.USER.send_message("me", report, disable_web_page_preview=True)
        await set_to_defaults(id)
        clone_cancel_key.pop(id, None)
    except Exception as e:
        import traceback
        traceback.print_exc()
        bot.LOGGER(__name__).error(e)
        bot.LOGGER(__name__).error(traceback.format_exc())
        await m.edit_text(f"An Error Occurred! \n\nError: {e}")
