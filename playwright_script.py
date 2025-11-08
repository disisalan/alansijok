from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from playwright.sync_api import sync_playwright, TimeoutError
from datetime import datetime
from typing import List, Dict, Optional
import time
from starlette.concurrency import run_in_threadpool


app = FastAPI(title="Flight Scraper API", version="1.0.0")

def set_input_value_and_dispatch(page, selector, value):
    """
    Set the value of an input via JS and dispatch input/change events so Angular hears it.
    Returns True if selector exists and script ran.
    """
    script = f"""
    (function(){{
        const el = document.querySelector("{selector}");
        if (!el) return false;
        el.focus();
        el.value = "{value}";
        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        var kd = new KeyboardEvent('keydown', {{bubbles:true, cancelable:true, key:'{value[0] if value else ""}'}}); 
        el.dispatchEvent(kd);
        var ku = new KeyboardEvent('keyup', {{bubbles:true, cancelable:true, key:'{value[0] if value else ""}'}}); 
        el.dispatchEvent(ku);
        return true;
    }})();
    """
    try:
        return page.evaluate(script)
    except Exception:
        return False

def extract_flight_data(page) -> List[Dict]:
    """
    Extract flight information from the search results page.
    Returns a list of flight dictionaries.
    """
    flights = []
    
    try:
        # Get all flight cards
        flight_cards = page.locator('.card-body').all()
        
        for index, card in enumerate(flight_cards):
            try:
                flight = {}
                
                # Airline name and flight number
                airline_name = card.locator('p.h6.responsive-bold.mb-0').first
                flight_number = card.locator('p.mb-0.d-inline.d-lg-block').first
                flight['airline'] = airline_name.text_content().strip() if airline_name.count() > 0 else ''
                flight['flight_number'] = flight_number.text_content().strip() if flight_number.count() > 0 else ''
                
                # Origin details
                origin_code = card.locator('.text-extra-dark.font-weight-600.mb-0.text-nowrap').first
                origin_time = card.locator('.text-mild-dark.d-block.h4').first
                origin_date = card.locator('.hide-on-small-and-down.mb-0.d-block').first
                origin_city = card.locator('.font-weight-normal.small.mb-0.text-nowrap.text-light-dark').first
                origin_terminal = card.locator('.font-weight-normal.small.text-light-dark').first
                
                flight['origin'] = origin_code.text_content().strip() if origin_code.count() > 0 else ''
                flight['origin_city'] = origin_city.text_content().strip() if origin_city.count() > 0 else ''
                flight['departure_time'] = origin_time.text_content().strip() if origin_time.count() > 0 else ''
                flight['departure_date'] = origin_date.text_content().strip() if origin_date.count() > 0 else ''
                flight['origin_terminal'] = origin_terminal.text_content().strip() if origin_terminal.count() > 0 else ''
                
                # Destination details (using nth elements)
                dest_elements = card.locator('.text-extra-dark').all()
                dest_code = dest_elements[1] if len(dest_elements) > 1 else None
                
                dest_time_elements = card.locator('.text-mild-dark.d-block.h4').all()
                dest_time = dest_time_elements[1] if len(dest_time_elements) > 1 else None
                
                dest_date_elements = card.locator('.hide-on-small-and-down.mb-0.d-block').all()
                dest_date = dest_date_elements[1] if len(dest_date_elements) > 1 else None
                
                dest_city_elements = card.locator('.font-weight-normal.small.mb-0.text-nowrap.text-light-dark').all()
                dest_city = dest_city_elements[1] if len(dest_city_elements) > 1 else None
                
                flight['destination'] = dest_code.text_content().strip() if dest_code else ''
                flight['destination_city'] = dest_city.text_content().strip() if dest_city else ''
                flight['arrival_time'] = dest_time.text_content().strip() if dest_time else ''
                flight['arrival_date'] = dest_date.text_content().strip() if dest_date else ''
                
                # Duration and stops
                duration = card.locator('.responsive-dblock.text-extra-dark.font-weight-bold').first
                flight['duration'] = duration.text_content().strip() if duration.count() > 0 else ''
                
                stops_info = card.locator('.onechangecolor.font-weight-bold.responsive-dblock').first
                flight['stops'] = stops_info.text_content().strip() if stops_info.count() > 0 else 'Non-stop'
                
                # Layover information
                if stops_info.count() > 0:
                    layover = stops_info.get_attribute('data-balloon')
                    flight['layover_info'] = layover.strip() if layover else ''
                else:
                    flight['layover_info'] = ''
                
                # Price
                price = card.locator('.text-gray.roboto_font.mb-0.text-primary.h4, .font-weight-600.text-gray.lbl-bold.roboto_font.mb-0.lbl-huge').first
                flight['price'] = price.text_content().strip() if price.count() > 0 else ''
                
                # Promotional offers
                promo = card.locator('.lbl-PromoFare.mb-0').first
                flight['promo'] = promo.text_content().strip() if promo.count() > 0 else ''
                
                # Baggage information
                baggage_elements = card.locator('.action-bar .text').all()
                checkin_baggage = ''
                hand_baggage = ''
                
                for el in baggage_elements:
                    text = el.text_content().strip()
                    if 'Kgs' in text:
                        if '/' in text:
                            checkin_baggage = text.split('/')[0].strip()
                        elif not checkin_baggage:
                            checkin_baggage = text
                        else:
                            hand_baggage = text
                
                flight['checkin_baggage'] = checkin_baggage
                flight['hand_baggage'] = hand_baggage
                
                # Available seats
                seats_info = card.locator('.action-bar .text.ng-binding').first
                if seats_info.count() > 0:
                    seats_text = seats_info.text_content().strip()
                    if 'Seat' in seats_text:
                        flight['available_seats'] = seats_text
                    else:
                        flight['available_seats'] = ''
                else:
                    flight['available_seats'] = ''
                
                # Next day arrival indicator
                next_day = card.locator('.text-danger').first
                flight['next_day_arrival'] = next_day.text_content().strip() if next_day.count() > 0 else ''
                
                flights.append(flight)
                
            except Exception as err:
                print(f'Error extracting flight at index {index}: {err}')
        
        return flights
        
    except Exception as e:
        print(f"Error extracting flight data: {e}")
        return []

def select_city(page, selector, city_name, field_name):
    """
    Generic function to select a city in an input field.
    """
    print(f"Selecting {field_name}: {city_name}")
    
    try:
        # Wait for the input field
        page.wait_for_selector(selector, timeout=15000)
        
        # Use JS to set value and dispatch events
        ok = set_input_value_and_dispatch(page, selector, city_name)
        if not ok:
            print("JS injection fallback failed, typing manually...")
            inp = page.locator(selector)
            inp.click()
            inp.fill("")
            inp.type(city_name, delay=80)
        
        # Wait for dropdown to populate
        page.wait_for_timeout(2200)
        
        # Select first suggestion using keyboard
        page.keyboard.press("ArrowDown")
        page.wait_for_timeout(250)
        page.keyboard.press("Enter")
        
        # Wait for selection to propagate
        page.wait_for_timeout(1200)
        
        return True
        
    except TimeoutError:
        print(f"Timed out waiting for {field_name} input")
        return False
    except Exception as e:
        print(f"Unexpected error selecting {field_name}: {e}")
        return False

def select_date(page, date_str):
    """
    Select the journey date on the calendar.
    date_str should be in format: YYYY-MM-DD
    """
    print(f"Selecting date: {date_str}")
    
    try:
        # Parse the date
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        day = date_obj.day
        
        # Click on the date picker input to open calendar
        date_input_selector = "input[placeholder='Select Journey Date']"
        page.wait_for_selector(date_input_selector, timeout=10000)
        page.locator(date_input_selector).click()
        
        # Wait for calendar to appear
        page.wait_for_timeout(1000)
        
        # Find and click the date
        # The calendar uses data-date attribute or aria-label with the date
        date_selector = f"td[data-day='{day}']:not(.disabled)"
        page.wait_for_selector(date_selector, timeout=5000)
        
        # Click the date
        date_cells = page.locator(date_selector).all()
        if date_cells:
            date_cells[0].click()
            page.wait_for_timeout(500)
            print(f"Date {day} selected successfully")
            return True
        else:
            print(f"Could not find date {day}")
            return False
            
    except Exception as e:
        print(f"Error selecting date: {e}")
        return False

def scrape_flights(origin: str, destination: str, journey_date: str) -> List[Dict]:
    """
    Main scraping function that can be called from FastAPI endpoint.
    
    Args:
        origin: Origin city name
        destination: Destination city name
        journey_date: Journey date in YYYY-MM-DD format
    
    Returns:
        List of flight dictionaries
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            print(f"Searching flights: {origin} → {destination} on {journey_date}")
            
            # Navigate to website
            page.goto("https://www.budgetticket.in", wait_until="domcontentloaded", timeout=60000)
            print("Page loaded successfully")
            
            # Select Origin
            origin_selector = "#anguScroll_value"
            origin_success = select_city(page, origin_selector, origin, "Origin")
            
            if not origin_success:
                raise Exception("Failed to select origin city")
            
            time.sleep(0.5)
            
            # Select Destination
            destination_selector = "input[placeholder='Select Destination City']"
            destination_success = select_city(page, destination_selector, destination, "Destination")
            
            if not destination_success:
                raise Exception("Failed to select destination city")
            
            time.sleep(0.5)
            
            # Select Date
            date_success = select_date(page, journey_date)
            
            if not date_success:
                print("Warning: Date selection may have failed, continuing anyway...")
            
            time.sleep(1)
            
            # Click Search Button
            search_button_selector = "input[type='submit'][ng-click='Search(false)']"
            page.wait_for_selector(search_button_selector, timeout=10000)
            page.locator(search_button_selector).click()
            
            print("Search button clicked, waiting for results...")
            
            # Wait for results to load
            time.sleep(8)
            
            # Extract flight data
            flights_data = extract_flight_data(page)
            
            print(f"Extracted {len(flights_data)} flight(s)")
            
            return flights_data

        except Exception as e:
            print(f"Error during scraping: {e}")
            raise
        finally:
            browser.close()

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Flight Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "/flight-search": "Search for flights with query parameters: origin, destination, journey_date"
        }
    }

@app.get("/flight-search")
async def search_flights(
    origin: str = Query(..., description="Origin city name (e.g., Bangalore)"),
    destination: str = Query(..., description="Destination city name (e.g., Delhi)"),
    journey_date: str = Query(..., description="Journey date in YYYY-MM-DD format (e.g., 2025-10-18)")
):
    """
    Search for flights between two cities on a specific date.
    Example: /flight-search?origin=Bangalore&destination=Delhi&journey_date=2025-10-18
    """
    try:
        # Validate date format
        try:
            datetime.strptime(journey_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Please use YYYY-MM-DD (e.g., 2025-10-18)"
            )

        # Run the blocking sync Playwright scraper in a threadpool so it doesn't block FastAPI event loop
        flights = await run_in_threadpool(scrape_flights, origin, destination, journey_date)

        if not flights:
            return JSONResponse(
                content={
                    "origin": origin,
                    "destination": destination,
                    "journey_date": journey_date,
                    "flights": [],
                    "message": "No flights found for the given search criteria"
                },
                status_code=200
            )

        return JSONResponse(
            content={
                "origin": origin,
                "destination": destination,
                "journey_date": journey_date,
                "total_flights": len(flights),
                "flights": flights
            },
            status_code=200
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error scraping flights: {str(e)}"
        )
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)