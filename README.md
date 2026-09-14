## Black Friday Data "Challenge"

*Can it be a challenge if there is no right answer?*

### Overview

This exercise is intended for students or anyone else interested in playing along. It offers a simple dataset like one might find in an ERP and a simple question, but with enough ambiguity that there is no correct solution. It can serve as a discussion point for students about the vagaries of real world data and the importance of precise question framing. More broadly, I like to think it can be a hopeful exercise for students concerned about the future of data jobs in the age of AI. Language models cannot solve what language itself cannot solve. 

I appreciate when instructors collect answer in a Google Form and are willing to shar the answers with me. So far, we've seen answers clump in clusters of similar assumptions with values between $700K-$14M. 

This is **not** about data quality. The data is not mistaken, persay. Just challenging, as most data is. 

### Key Materials

- The key question to be answered is: "How much did our stores make over Black Friday?" 
- `data.csv`: The data file provided to students 
- `full.csv`: A fuller version of the dataset before some censoring
- `dgp.py`: The script that generates the data files

### Potential Snags / Degrees of Freedom

**Question Framing**

- Does "stores" mean physical stores? Or does it generically mean "all places where buying can occur"? There's a high-volume online channel, but it's only identifiable by being tagged as "OL" in the state column.
- Does "Black Friday" literally mean Friday only? Or does it now mean the full Black Friday to Cyber Monday weekend when "Black Friday sales" are held? Note that sales are elevated this entire period
- What does "make" mean? Revenue? Profit? We have no data on the cost of merchandise sold.

**Data Semantics**

- Systems of records can change the time zone. Did they consider whether the timezone is localized for each store or universal? Should the localized ones be backed out? (Technically, all timezones here are UTC) 
- Could they even back out the right timezones if they wanted to? How would you handle "Online"? How would you handle states like Indiana or Texas that sit across multiple timezones? 
- There is a field for the discount that takes a value of 0.1, 0.2, or 0.3. Does the transaction amount already include this or not? Does it already include tax or not?
- In the payment type field, we have Credit, Debit, Cash, or Returns. So, some of these "transactions" are not purchase transactions but return transactions. Should they be ignored? Or subtracted from the total? 

**Data Structure**

- The dataset contains both a transaction date and a posting date (when the transaction was charged to the form of payment). However, the table only receives new records after the charge is made. This creates censoring. For example, in-store transactions are loaded after 1 day, but online orders are only loaded after they ship (where the charge happens on shipping). Online orders >$100 receive fast shipping so are loaded after 3 days, but online orders <$100 are shipped after a week so are not loaded for 7 days. Thus, some online transactions may not be available yet. 

**Data Quality**

- How are there "Cash" purchases for "Online" orders? That seems wrong, but we'll never know. 
- For one single store ID, there are no transactions the Sunday of Black Friday weekend. Closed? Data glitch? Who knows. 
