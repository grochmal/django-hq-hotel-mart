README for django-hq-hotel-mart

## Introduction

Django app for constructing and reloading the data mart in the Hotel Quickly
example Warehouse.

Two command line tools are present in the hotel mart:

*   `hqm-pop-hours`: Populates the time frame the data mart shall load data
    for, this is used to configure the mart for given years.

*   `hqm-reload`: Fetches the actual data (offers) from the warehouse according
    to the time frame the mart will work for.

Their usage:

    hqm-pop-hours [-hvt] -y <4 digit year>

      -h  Print usage.
      -v  Be verbose, print successes as well as errors.
      -t  Truncate the hour table before inserting.
      -y  A four digit year (e.g. 2016) to load the hour table with.

    ------

    hqm-reload [-hvt]

      -h  Print usage.
      -v  Be verbose, print successes as well as errors.
      -t  Truncate the currency, offer and hoteloffer tables before beginning
          the insert, this is useful to reload the mart from scratch.

The main purpose of the data mart is an `API` that enables us to query cheapest
fares for hotels based on the offers.  This `API` can be called as follows:

    GET /api/?queryAt=2015-11-11T11&hotelId=169&checkinDate=2015-11-13&checkoutDate=2015-11-14 HTTP/1.1
    Host: ...

    ...

    HTTP/1.1 200 OK
    Content-Type: application/json

    {
    ,   "checkinDate": "2013-05-30"
    ,   "checkoutDate": "2013-05-31"
    ,   "sellingPrice": "650.0000000000"
    ,   "currencyCode": "GBP"
    ,   "hotelId": 169
    ,   "offerId": 2
    }

Errors are returned in HTTP codes, notably `400` for bad requests.  All `GET`
arguments must be provided and they are:

*   `queryAt`: The moment in time the query is made, this is needed because we
    do not have data for the current time.  In a real world situation the mart
`API` would use the current date and time but it is not possible with
historical data.  The argument is an ISO data followed by `T` and a two digit
hour (e.g. `2015-11-11T11` is November the 11th, 2015, at 11AM).

*   `hotelId`: The hotel for which we are checking prices, it is an integer
    value.

*   `checkinDate`: An ISO 8601 date, the day for which we are planning to start
    our stay at the hotel.

*   `checkoutDate`: And ISO 8601 date, the last day of our stay.

## Time frames

A data mart only needs the data it will work with and, most often, this data
changes over time.  The present mart can be configured for a certain time frame
represented in years.  For example to be able to calculate best offers within
the 2015 and 2016 years we would do:

    hqm-pop-hours -t -y 2015
    hqm-pop-hours -y 2016
    hqm-reload

Note that we are using `-t` to truncate the tables at the beginning of the
load, this is intended.  One the data in the mart becomes obsolete we can drop
that data and reload new data from the warehouse.  Nothing stops us from
loading 2017 without truncating the tables and then reloading data from the
warehouse, yet that would result in a mart that has too much of historical
data.

Instead it is better to create a mart for 2016 and 2017, load the data into it
and switch the marts.  Then, truncate the first mart and prepare it to be
loaded with data for 2017 and 2018.  And so on.

This result in marts with less data, and therefore faster queries.

## Copying

Copyright (C) 2016 Michal Grochmal

This file is part of `django-hq-hotel-mart`.

`django-hq-hotel-mart` is free software; you can redistribute and/or modify all
or parts of it under the terms of the GNU General Public License as published
by the Free Software Foundation; either version 3 of the License, or (at your
option) any later version.

`django-hq-hotel-mart` is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
details.

The COPYING file contains a copy of the GNU General Public License.  If you
cannot find this file, see <http://www.gnu.org/licenses/>.

