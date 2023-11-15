from typing import Sequence

from app.base import do, enums, vo
from app.persistence.database.util import (
    PostgresQueryExecutor,
    generate_query_parameters,
)


async def browse(
        name: str | None = None,
        city_id: int | None = None,
        district_id: int | None = None,
        sport_id: int | None = None,
        limit: int = 10,
        offset: int = 0,
) -> Sequence[vo.ViewStadium]:
    criteria_dict = {
        'name': (f'%{name}%' if name else None, 'stadium.name LIKE %(name)s'),
        'city_id': (city_id, 'district.city_id = %(city_id)s'),
        'district_id': (district_id, 'district.id = %(district_id)s'),
        'sport_id': (sport_id, 'venue.sport_id = %(sport_id)s'),
    }

    query, params = generate_query_parameters(criteria_dict=criteria_dict)

    where_sql = 'WHERE ' + ' AND '.join(query) if query else ''

    results = await PostgresQueryExecutor(
        sql=fr'SELECT stadium.id, stadium.name, district_id, contact_number,'
            fr'       description, long, lat,'
            fr'       city.name,'
            fr'       district.name,'
            fr'       ARRAY_AGG(DISTINCT sport.name),'
            fr'       ARRAY_AGG(DISTINCT business_hour.*)'
            fr'  FROM stadium'
            fr' INNER JOIN district ON stadium.district_id = district.id'
            fr' INNER JOIN city ON district.city_id = city.id'
            fr' INNER JOIN venue ON stadium.id = venue.stadium_id'
            fr' INNER JOIN sport ON venue.sport_id = sport.id'
            fr' INNER JOIN business_hour ON business_hour.place_id = stadium.id'
            fr'                         AND business_hour.type = %(place_type)s'
            fr' {where_sql}'
            fr' GROUP BY stadium.id, city.id, district.id'
            fr' ORDER BY stadium.id'
            fr' LIMIT %(limit)s OFFSET %(offset)s',
        limit=limit, offset=offset, place_type=enums.PlaceType.stadium, fetch='all', **params,
    ).execute()

    return [
        vo.ViewStadium(
            id=id_,
            name=name,
            district_id=district_id,
            contact_number=contact_number,
            description=description,
            long=long,
            lat=lat,
            city=city,
            district=district,
            sports=[name for name in sport_names],
            business_hours=[
                do.BusinessHour(
                    id=bid,
                    place_id=place_id,
                    type=place_type,
                    weekday=weekday,
                    start_time=start_time,
                    end_time=end_time,
                ) for bid, place_id, place_type, weekday, start_time, end_time in business_hours
            ],
        )
        for id_, name, district_id, contact_number, description, long, lat, city, district,
        sport_names, business_hours in results
    ]


async def read(stadium_id: int) -> vo.ViewStadium:
    result = await PostgresQueryExecutor(
        sql=fr'SELECT stadium.id, stadium.name, district_id, contact_number,'
            fr'       description, long, lat,'
            fr'       city.name,'
            fr'       district.name,'
            fr'       ARRAY_AGG(DISTINCT sport.name),'
            fr'       ARRAY_AGG(DISTINCT business_hour.*)'
            fr'  FROM stadium'
            fr' INNER JOIN district ON stadium.district_id = district.id'
            fr' INNER JOIN city ON district.city_id = city.id'
            fr' INNER JOIN venue ON stadium.id = venue.stadium_id'
            fr' INNER JOIN sport ON venue.sport_id = sport.id'
            fr' INNER JOIN business_hour ON business_hour.place_id = stadium.id'
            fr'                         AND business_hour.type = %(place_type)s'
            fr' WHERE stadium.id = %(stadium_id)s'
            fr' GROUP BY stadium.id, city.id, district.id'
            fr' ORDER BY stadium.id',
        fetch=1, place_type=enums.PlaceType.stadium, stadium_id=stadium_id,
    ).execute()

    id_, name, district_id, contact_number, description, long, lat, city, district, sport_names, business_hours = result

    return vo.ViewStadium(
        id=id_,
        name=name,
        district_id=district_id,
        contact_number=contact_number,
        description=description,
        long=long,
        lat=lat,
        city=city,
        district=district,
        sports=[name for name in sport_names],
        business_hours=[
            do.BusinessHour(
                id=bid,
                place_id=place_id,
                type=place_type,
                weekday=weekday,
                start_time=start_time,
                end_time=end_time,
            ) for bid, place_id, place_type, weekday, start_time, end_time in business_hours
        ],
    )
