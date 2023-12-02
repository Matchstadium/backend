from typing import Sequence

from app.base import do, enums, vo
from app.persistence.database.util import (
    PostgresQueryExecutor,
    generate_query_parameters,
)


async def browse(
        place_type: enums.PlaceType,
        place_id: int,
        time_ranges: Sequence[vo.WeekTimeRange] = None,
) -> Sequence[do.BusinessHour]:
    criteria_dict = {
        'place_type': (place_type, 'type = %(place_type)s'),
        'place_id': (place_id, 'place_id = %(place_id)s'),
    }
    query, params = generate_query_parameters(criteria_dict=criteria_dict)

    raw_or_query = []
    if time_ranges:
        for i, time_range in enumerate(time_ranges):
            time_range: vo.WeekTimeRange
            raw_or_query.append(f"""({' AND '.join([
                f'business_hour.weekday = %(weekday_{i})s',
                f'business_hour.start_time <= %(end_time_{i})s',
                f'business_hour.end_time >= %(start_time_{i})s'
            ])})""")
            params.update({
                f'weekday_{i}': time_range.weekday,
                f'end_time_{i}': time_range.end_time,
                f'start_time_{i}': time_range.start_time,
            })
    or_query = ' OR '.join(raw_or_query)

    where_sql = 'WHERE ' + ' AND '.join(query) if query else ''
    where_sql += (' AND ' if where_sql else 'WHERE ') + or_query if or_query else ''

    results = await PostgresQueryExecutor(
        sql=fr'SELECT id, place_id, type, weekday, start_time, end_time'
            fr'  FROM business_hour'
            fr' {where_sql}'
            fr' ORDER BY id',
        **params,
    ).fetch_all()

    return [
        do.BusinessHour(
            id=id_,
            place_id=place_id,
            type=type_,
            weekday=weekday,
            start_time=start_time,
            end_time=end_time,
        )
        for id_, place_id, type_, weekday, start_time, end_time in results
    ]
