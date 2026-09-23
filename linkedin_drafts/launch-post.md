# LinkedIn launch post — Who gets the grants?

I can tell you, to the euro, what every computer scientist in Europe won in ERC grants since 2007. 💶

I cannot tell you how many courses most of them taught last year.

That asymmetry is the whole story, and I only understood how bad it is by trying to build the thing that would fix it: 👉 https://alexjungaalto.github.io/who-gets-the-grants/

Click any European country and you get the computer scientists who secured the most competitive research funding there — €1.13 billion of ERC "Computer Science and Informatics" money across 722 grants, plus the national agencies for Austria (FWF) and Finland (Research Council of Finland). 2,225 researchers, 25 countries, every grant listed with its title and its budget.

A few things that fall out in one click:

🇩🇪 Germany leads the ERC table with €225M, ahead of 🇫🇷 France (€152M) and 🇬🇧 the UK (€144M).
🇮🇱 Israel, an associated country, has won €138M — more than Switzerland, Spain or the Netherlands.
🏆 The single biggest ERC-funded computer scientist in the set is Daniel Cremers (TU München), with €7.8M across five grants.
🇦🇹 In Austria, Sepp Hochreiter's Cluster of Excellence "Bilateral AI" alone is €20M of FWF money — the largest single line in the Austrian column.

Now the part I did not expect.

**The funding data is magnificent. The teaching data barely exists.**

Grant money is tracked to the cent, by person, by year, by panel, in public APIs that have been maintained for two decades. That is what a system does when it takes something seriously.

Teaching? I could retrieve course counts for exactly **four universities in Finland**, because Finland runs a shared student-information system with a public read-only API. Eighty researchers in the whole dataset have a number in that column.

For Austria — a country whose universities I teach at — I got **zero**. Not "they don't teach". Zero *retrievable*. TU Wien's course catalogue is a JavaScript application that returns nothing to a script; JKU's returns 403 to anything that isn't a browser. So I tried the back door and searched YouTube for recorded lectures from the 236 best-funded people on the list. After hand-checking every hit, 26 have a genuine lecture series. Austrians with one: also zero.

We have built an infrastructure that can answer "who brought in the money?" instantly, in 25 countries, and cannot answer "who taught the students?" in most of them at all. Then we wonder why one of those counts for tenure and the other doesn't. You cannot reward what you refuse to record. 📊

So let me use the one column I could fill to name people doing the opposite — putting their teaching on the public record where anyone can see it:

🎓 Jean-Daniel Boissonnat, Nicholas Ayache and Wendy Mackay, with full lecture courses published through the Collège de France.
🎓 Marlon Dumas (Tartu), 20 lectures of Business Process Management, free to the world.
🎓 Ron Kimmel (Technion) publishing entire numbered courses; Aki Vehtari (Aalto) with his Bayesian Data Analysis course; Jukka Suomela (Aalto) with Distributed Algorithms; Cecilia Mascolo (Cambridge) with Mobile Health.
🎓 And Daniel Cremers again — top of the funding table *and* 15 lectures of Variational Methods for Computer Vision online. The two are not in conflict. That is rather the point.

Now the honest part, because this is assembled data and you should treat it as such:

⚠️ The numbers may be wrong, and the site says so above the fold. Funders record principal investigators as one unseparated string, so names are reconstructed statistically — a researcher can be split in two, or two people with one surname merged. Consortium grants are credited whole to whoever the funder names, which flatters coordinators.
⚠️ Only the ERC column is comparable across countries. Austria and Finland look richer only because theirs are the two national agencies I have added so far.
⚠️ A blank or a zero means **not found**, never "none". That applies to every teaching cell, and I would rather be accused of gaps than of insinuation.

Everything — data, scripts, the lot — is open: https://github.com/alexjungaalto/who-gets-the-grants

If your row is wrong, tell me and I will fix it. And if you work at a university whose course catalogue a machine can read, I would genuinely love to add it. That is the column that needs filling. 🙂

#HigherEducation #ResearchFunding #ERC #OpenData #Teaching #Academia #ComputerScience #Europe

---
## Notes for posting

- Every figure verified against the published dataset on 2026-09-23: ERC PE6 €1,131M / 722 PI-grants / 2,225 people / 25 countries; DE €225M, FR €152M, UK €144M, IL €138M; Cremers €7.80M in 5 grants; Hochreiter €20.1M FWF; 80 people with course counts (4 Finnish universities); 236 searched on YouTube, 26 with a verified lecture series; Austria zero on both.
- Suggested image: screenshot of the Finland panel — it is the only one where the ERC, national-funder, course-count and lecture columns are all populated side by side, which makes the argument visually in one glance.
- The post deliberately does NOT claim that big grant winners teach less. The data cannot support that and the draft says so. If anyone pushes that reading in the comments, correct it — the claim is about what we *measure*, not about individuals.
- Continues the argument from the 2026-09-16 post ("count great teaching"); this is the evidence half. Safe to cross-reference it in a comment rather than in the post body.
- Shorter alternative opening if the first two lines feel too clever:
  "I built a map of who wins Europe's computer-science research money. The hard part wasn't the money — it was finding out whether any of them teach."
