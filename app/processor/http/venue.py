from typing import Sequence, Optional

from fastapi import APIRouter, Depends, Query, responses
from pydantic import BaseModel

import app.exceptions as exc
import app.persistence.database as db
from app.base import do, enums, vo
from app.middleware.headers import get_auth_token
from app.utils import Limit, Offset, Response, context

router = APIRouter(
    tags=['Venue'],
    default_response_class=responses.JSONResponse,
)


class VenueSearchParameters(BaseModel):
    name: str | None = Query(default=None)
    stadium_id: int | None = Query(default=None)
    sport_id: int | None = Query(default=None)
    is_reservable: bool | None = Query(default=None)
    sort_by: enums.VenueAvailableSortBy = Query(default=enums.VenueAvailableSortBy.current_user_count)
    order: enums.Sorter = Query(default=enums.Sorter.desc)
    limit: int = Limit
    offset: int = Offset


class BrowseVenueOutput(BaseModel):
    data: Sequence[do.Venue]
    total_count: int
    limit: int
    offset: int


@router.get('/venue')
async def browse_venue(params: VenueSearchParameters = Depends()) -> Response[BrowseVenueOutput]:
    venues, total_count = await db.venue.browse(
        name=params.name,
        sport_id=params.sport_id,
        stadium_id=params.stadium_id,
        is_reservable=params.is_reservable,
        sort_by=params.sort_by,
        order=params.order,
        limit=params.limit,
        offset=params.offset,
    )
    return Response(
        data=BrowseVenueOutput(
            data=venues, total_count=total_count,
            limit=params.limit, offset=params.offset,
        ),
    )


@router.get('/venue/{venue_id}')
async def read_venue(venue_id: int) -> Response[do.Venue]:
    venue = await db.venue.read(venue_id=venue_id)
    return Response(data=venue)


@router.get('/venue/{venue_id}/court')
async def browse_court_by_venue_id(venue_id: int) -> Response[Sequence[do.Court]]:
    courts = await db.court.browse(venue_id=venue_id)
    return Response(data=courts)


class EditVenueInput(BaseModel):
    name: str | None = None
    floor: str | None = None
    area: int | None = None
    capacity: int | None = None
    sport_id: int | None = None
    is_reservable: bool | None = None
    reservation_interval: int | None = None
    is_chargeable: bool | None = None
    fee_rate: float | None = None
    fee_type: enums.FeeType | None = None
    sport_equipments: str | None = None
    facilities: str | None = None
    court_type: str | None = None


@router.patch('/venue/{venue_id}')
async def edit_venue(venue_id: int, data: EditVenueInput, _=Depends(get_auth_token)) -> Response:
    venue = await db.venue.read(venue_id=venue_id, include_unpublished=True)
    stadium = await db.stadium.read(stadium_id=venue.stadium_id, include_unpublished=True)

    if stadium.owner_id != context.account.id:
        raise exc.NoPermission

    await db.venue.edit(
        venue_id=venue.id,
        **data.model_dump(),
    )
    return Response()


class AddVenueInput(BaseModel):
    stadium_id: int
    name: str
    floor: str
    reservation_interval: Optional[int]
    is_reservable: bool
    is_chargeable: bool
    fee_rate: Optional[float]
    fee_type: Optional[enums.FeeType]
    area: int
    capacity: int
    sport_equipments: Optional[str]
    facilities: Optional[str]
    court_count: int
    court_type: str
    sport_id: int
    business_hours: Sequence[vo.WeekTimeRange]


class AddVenueOutput(BaseModel):
    id: int


@router.post('/venue')
async def add_venue(data: AddVenueInput, _=Depends(get_auth_token)) -> Response[AddVenueOutput]:
    stadium = await db.stadium.read(stadium_id=data.stadium_id)

    if stadium.owner_id != context.account.id or context.account.role != enums.RoleType.provider:
        raise exc.NoPermission

    id_ = await db.venue.add(
        stadium_id=data.stadium_id,
        name=data.name,
        floor=data.floor,
        reservation_interval=data.reservation_interval,
        is_reservable=data.is_reservable,
        is_chargeable=data.is_chargeable,
        fee_rate=data.fee_rate,
        fee_type=data.fee_type,
        area=data.area,
        capacity=data.capacity,
        sport_equipments=data.sport_equipments,
        facilities=data.facilities,
        court_count=data.court_count,
        court_type=data.court_type,
        sport_id=data.sport_id,
    )

    # await db.business_hour.batch_add(
    #     place_type=enums.PlaceType.venue,
    #     place_id=id_,
    #     business_hours=data.business_hours,
    # )

    return Response(data=AddVenueOutput(id=id_))
