import sqlite3
import time
import uuid
import datetime
from typing import Union, List, Tuple


class User(object):
    def __init__(self, chat_id: int, name: str):
        self.id = chat_id
        self.name = name


class Irrigation(object):
    def __init__(self, id, field_id, date, amount):
        self.id = id
        self.field_id = field_id
        self.date = date
        self.amount = amount


class NPK(object):
    def __init__(self, id, field_id, date, npk):
        self.id = id
        self.field_id = field_id
        self.date = date
        self.npk = npk


class Field(object):
    def __init__(
        self,
        id: int,
        name: str,
        creator_id: int,
        latitude: float,
        longitude: float,
        crop_start: datetime.date,
        crop_end: datetime.date,
        crop_name: str,
    ):
        self.id = id
        self.name = name
        self.creator_id = creator_id
        self.latitude = latitude
        self.longitude = longitude
        self.crop_start = crop_start
        self.crop_end = crop_end
        self.crop_name = crop_name


# All async in case we switch to Postgres
class Database(object):
    def __init__(self):
        self._db = sqlite3.connect("/home/db/agrobot.db")
        self._db.row_factory = sqlite3.Row

    async def get_all_users(self) -> List[User]:
        query = """
        SELECT id,
               name
        FROM users
        """
        cursor = self._db.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()

        return [User(row["id"], row["name"]) for row in rows]

    async def get_user(self, chat_id) -> Union[User, None]:
        query = """
        SELECT id,
               name
        FROM users
        WHERE id = ?
        """
        args = (chat_id,)
        cursor = self._db.cursor()
        cursor.execute(query, args)
        row = cursor.fetchone()
        cursor.close()

        if row:
            return User(row["id"], row["name"])
        else:
            return None

    async def new_user(self, chat_id: int, name: str) -> User:
        query = """
        INSERT or REPLACE INTO users (id, name)
        VALUES (?, ?)
        """
        args = (chat_id, name)

        cursor = self._db.cursor()
        cursor.execute(query, args)
        self._db.commit()
        cursor.close()

        return User(chat_id, name)

    async def delete_user(self, id):
        query = """
        DELETE
        FROM users
        WHERE id = ?
        """
        args = (id,)
        cursor = self._db.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute(query, args)
        self._db.commit()
        cursor.close()

    async def get_user_fields(self, id) -> List[Field]:
        query = """
        SELECT *
        FROM fields
        WHERE creator_id = ?
        """
        args = (id,)
        cursor = self._db.cursor()
        cursor.execute(query, args)
        rows = cursor.fetchall()
        cursor.close()
        return [
            Field(
                row["id"],
                row["name"],
                row["creator_id"],
                row["latitude"],
                row["longitude"],
                row["crop_start"],
                row["crop_end"],
                row["crop_name"],
            )
            for row in rows
        ]

    async def get_user_fields_irrs_npks(self, id):
        all_fields = []
        for field in await self.get_user_fields(id):
            field_irrigations = await self.get_irrigations(field.id)
            field_npks = await self.get_npks(field.id)
            all_fields.append([field, field_irrigations, field_npks])
        return all_fields

    async def get_user_field_dicts(self, id):
        field_dict = {}
        triplets = await self.get_user_fields_irrs_npks(id)
        for field, field_irrigations, field_npks in triplets:
            irrigation_events = []
            irrigation_ammounts = []
            for field_irrigation in field_irrigations:
                irrigation_events.append(field_irrigation.date)
                irrigation_ammounts.append(field_irrigation.amount)

            npk_events = []
            npk = []
            for field_npk in field_npks:
                npk_events.append(field_npk.date)
                npk.append(field_npk.npk)

            field_dict[field.id] = {
                "name": field.name,
                "latitude": field.latitude,
                "longitude": field.longitude,
                "crop_start": field.crop_start,
                "crop_end": field.crop_end,
                "crop_name": field.crop_name,
                "irrigation_events": irrigation_events,
                "irrigation_ammounts": irrigation_ammounts,
                "npk_events": npk_events,
                "npk": npk,
            }
        return field_dict

    async def add_field(
        self,
        id: int,
        name: str,
        creator_id: int,
        latitude: float,
        longitude: float,
        crop_start: datetime.date,
        crop_end: datetime.date,
        crop_name: str,
    ):
        query = """
        INSERT or REPLACE INTO fields(id, name, creator_id, latitude, longitude, crop_start, crop_end, crop_name)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        args = (
            id,
            name,
            creator_id,
            latitude,
            longitude,
            crop_start.strftime("%Y-%m-%d"),
            crop_end.strftime("%Y-%m-%d"),
            crop_name,
        )
        cursor = self._db.cursor()
        cursor.execute(query, args)
        self._db.commit()
        cursor.close()

    async def delete_field(self, id):
        query = """
        DELETE
        FROM fields
        WHERE id = ?
        """
        args = (id,)
        cursor = self._db.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute(query, args)
        self._db.commit()
        cursor.close()

    async def get_field(self, id):
        query = """
        SELECT *
        FROM fields
        WHERE id = ?
        """
        args = (id,)
        cursor = self._db.cursor()
        cursor.execute(query, args)
        row = cursor.fetchone()
        cursor.close()
        if row:
            return row
        else:
            return None

    async def get_irrigations(self, field_id) -> List[Field]:
        query = """
        SELECT *
        FROM irrigations
        WHERE field_id = ?
        """
        args = (field_id,)
        cursor = self._db.cursor()
        cursor.execute(query, args)
        rows = cursor.fetchall()
        cursor.close()
        return [
            Irrigation(row["id"], row["field_id"], row["date"], row["amount"])
            for row in rows
        ]

    async def add_irrigation(self, id, field_id, date, amount):
        query = """
        INSERT or REPLACE INTO irrigations(id, field_id, date, amount)
               VALUES (?, ?, ?, ?)
        """
        args = (id, field_id, date.strftime("%Y-%m-%d"), amount)
        cursor = self._db.cursor()
        cursor.execute(query, args)
        self._db.commit()
        cursor.close()

    async def delete_irrigation(self, id: int):
        query = """
        DELETE
        FROM irrigations
        WHERE id = ?
        """
        args = (id,)
        cursor = self._db.cursor()
        cursor.execute(query, args)
        self._db.commit()
        cursor.close()

    async def get_npks(self, id) -> List[NPK]:
        query = """
        SELECT *
        FROM npks
        WHERE field_id = ?
        """
        args = (id,)
        cursor = self._db.cursor()
        cursor.execute(query, args)
        rows = cursor.fetchall()
        cursor.close()
        return [
            NPK(
                row["id"],
                row["field_id"],
                row["date"],
                [float(x) for x in row["npk"].split(" ")],
            )
            for row in rows
        ]

    async def add_npk(self, id, field_id, date, npk):
        query = """
        INSERT or REPLACE INTO npks(id, field_id, date, npk)
               VALUES (?, ?, ?, ?)
        """
        npk_str = " ".join(list(map(str, npk)))  # save as: [50,30,20] -> 50 30 20
        args = (id, field_id, date.strftime("%Y-%m-%d"), npk_str)
        cursor = self._db.cursor()
        cursor.execute(query, args)
        self._db.commit()
        cursor.close()

    async def delete_npk(self, id):
        query = """
        DELETE
        FROM npks
        WHERE id = ?
        """
        args = (id,)
        cursor = self._db.cursor()
        cursor.execute(query, args)
        self._db.commit()
        cursor.close()

    async def add_income(self, id, field_id, income_per_ga):
        query = """
        INSERT or REPLACE INTO income(id, field_id, income_per_ga)
               VALUES (?, ?, ?)
        """
        args = (id, field_id, income_per_ga)
        cursor = self._db.cursor()
        cursor.execute(query, args)
        self._db.commit()
        cursor.close()

    async def get_income(self, id):
        query = """
        SELECT *
        FROM income
        WHERE id = ?
        """
        args = (id,)
        cursor = self._db.cursor()
        cursor.execute(query, args)
        row = cursor.fetchone()
        cursor.close()

        if row:
            return row
        else:
            return None
