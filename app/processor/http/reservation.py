from typing import Sequence

from fastapi import APIRouter, responses
from pydantic import BaseModel

import app.exceptions as exc
import app.persistence.database as db
from app.base import do, enums, vo
from app.client import google_calendar
from app.utils import Limit, Offset, Response, context

router = APIRouter(
    tags=['Reservation'],
    default_response_class=responses.JSONResponse,
)


class BrowseReservationParameters(BaseModel):
    city_id: int | None = None
    district_id: int | None = None
    sport_id: int | None = None
    stadium_id: int | None = None
    time_ranges: Sequence[vo.DateTimeRange] | None = None
    technical_level: enums.TechnicalType | None = None
    limit: int = Limit
    offset: int = Offset
    sort_by: enums.BrowseReservationSortBy = enums.BrowseReservationSortBy.time
    order: enums.Sorter = enums.Sorter.desc


@router.post('/view/reservation')
async def browse_reservation(params: BrowseReservationParameters) -> Response[Sequence[do.Reservation]]:
    reservations = await db.reservation.browse(
        city_id=params.city_id,
        district_id=params.district_id,
        sport_id=params.sport_id,
        stadium_id=params.stadium_id,
        time_ranges=params.time_ranges,
        technical_level=params.technical_level,
        limit=params.limit,
        offset=params.offset,
        sort_by=params.sort_by,
        order=params.order,
    )

    return Response(
        data=reservations,
    )


@router.get('/reservation/{reservation_id}')
async def read_reservation(reservation_id: int) -> Response[do.Reservation]:
    reservation = await db.reservation.read(reservation_id=reservation_id)
    return Response(data=reservation)


@router.post('/reservation/code/{invitation_code}')
async def join_reservation(invitation_code: str) -> Response[bool]:
    account_id = context.account.id
    reservation = await db.reservation.read_by_code(invitation_code=invitation_code)

    if reservation.vacancy <= 0:
        raise exc.ReservationFull

    await db.reservation_member.batch_add(
        reservation_id=reservation.id,
        member_ids=[account_id],
    )

    await google_calendar.update_google_calendar_event(
        reservation_id=reservation.id,
        member_id=account_id,
    )

    return Response(data=True)
