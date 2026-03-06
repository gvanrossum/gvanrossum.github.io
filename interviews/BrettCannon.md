# Interview with Brett Cannon

This interview has been lightly edited for clarity, but kept close to the
original conversation.

**_Guido:_ I'm trying to piece together early history of the Python core dev
community and whatever personal recollections people have about how they found
Python, or how Python found them. Brett, how did you first hear about Python or
find out about it? Not when did you start contributing, but when did you first
read or write a line of Python?**

_Brett:_
In the fall of 2000, I was on the hunt for a language that could teach me a bit
of object-oriented programming because while I was at Berkeley, I was going to
take the intro CS courses.

**You were still in university then, right?**

Correct. I was doing my bachelor's degree. I was going to be in philosophy, but
I still wanted to take the computer science courses. I couldn't double
major for reasons, but I still wanted to take CS courses. The intro CS
course, CS 61A, has an entrance exam. And I was afraid there was going to be
potentially some object-oriented programming questions. I had already learned C
at that point. So I was searching for a language to basically learn a bit more
programming before I had to take that exam. Well, you could choose C++ or Java.

**Those would have been the obvious choices in 2000.**

I started to poke around for languages to learn object-oriented programming.

**Did you just type something into Google?**

I don't remember how I searched back then. It may have been Alta Vista or
HotBot or one of those early search engines.

**Alta Vista was good.**

Anyway, I kept running into advice like, Perl should be your sixth language, and
Python is a great first language. I tried Python and immediately liked it. I
read the tutorial in the docs, and I think I also read an O'Reilly book around
then: not Mark Lutz's *Programming Python* with the snake, but the smaller one,
*Learning Python*, with the mouse on the cover. I'm not sure if it was out yet,
but if it was, I read it -- I've always preferred books. **[It was. --Guido]**

**Was that by Alex Martelli?**

No, that was Mark Lutz.

**I forget which book Martelli was involved with.**

That was *Python Cookbook*. Anyway, I learned Python and loved it, and somewhat
ironically I didn't end up needing object-oriented programming for that entrance
exam after all. But I liked Python enough that I kept using it -- and I've been
using it ever since. So that's how I found Python, and Python found me.

**And you were the kind of person who was always coding little things or big things.**

Effectively. It was just a constant little project here or there, or I need to
do something for an assignment, and it's easier to write some Python code to get
it done, or what have you. So just any time I had an opportunity where I got to
choose the programming language, I was choosing Python at that time.

**What languages did you know before Python?**

C. Just C? A little Pascal, but not much. But yeah, pretty much just C at that
point.

**I think Pascal was already pretty much out of style by 2000.**

The Pascal course I took was a weird short class, not even a full term. They had
problems with the compiler and we couldn't do much with it. So at that point it
was pretty much just C for me. Going to Python was a very different world -- no
compiler hassles, and the REPL [Read-Eval-Print Loop] was a revelation.

**How soon after that did you get into the community?**
**When did you first start reading a Python mailing list or newsgroup?**

It depends how you define community. I believe the following year was when
ActiveState started the Python Cookbook website -- a place to upload and share
useful code snippets, things that weren't worth getting onto the Vaults of
Parnassus. That's what O'Reilly eventually turned into the *Python Cookbook*. I
submitted a couple of things, and that's how I got to know Alex Martelli -- I
submitted a recipe that ended up in the first edition of the *Cookbook*.

**What recipe was that?**

It was actually the largest and last recipe in the book: a pure Python implementation
of `strptime`, which wasn't available on Windows at the time. I didn't like my
first version because you had to supply all the locale information, but I
figured out how to reverse-engineer it. That's what led me into core
development: in May 2002, the week after I graduated, I asked Alex how to get it
into the standard library. He pointed me to python-dev. I sent the email in
mid-June, François Pinard responded and helped me through the process, and about a
month later `time.strptime` was in. I never unsubscribed.

**When did you start posting your python-dev summaries?**

August of 2002, I think.

**The same year. That was quick!**

My bachelor's was in philosophy, and I'd taken the intro CS and the undergrad AI
course at Cal. I wanted a double major, but for unit cap reasons in the UC
system I couldn't. I decided I wanted to go to grad school in CS, but not having
a bachelor's in it might be a hindrance, so I took a gap year to build my
credentials and apply to grad programs. That's why I had the time to get so
involved: when I submitted `strptime`, I had such a great experience that I
decided to stick around and follow python-dev. I kept enjoying interacting with
everybody. Then I noticed the python-dev summaries weren't being maintained
anymore -- Andrew Kuchling had originally done them but didn't have the
bandwidth. So I volunteered.

**Andrew Kuchling was doing the summaries before you?**

Yes. He stopped, and I picked them up. I think he was at CNRI at that point,
working with Neil on Quixote -- their web framework thing. They had a special
DSL for strings where you didn't print them in order to have them show up in the
output.

**Many people have tried things like that.**
**They usually find out it's not great to be so implicit.**

Anyway, I figured the summaries were a good learning opportunity -- I was
reading the emails anyway, and it gave me a chance to ask "stupid" questions
that everyone was happy to answer. I picked them up in August or September 2002.

**That's a great intro to the community.**

It was great. Everyone learned who I was very quickly, and I was able to ask
questions easily.

**Everybody is a big fan because it's something they want to have,**
**but not something they want to volunteer to do.**

Exactly. I didn't do it for that, but it did turn out that core devs got to know
me because I was there reading stuff and asking questions, and people who
weren't directly involved could keep up through the summaries. I did them for a
few years -- I think I stopped sometime during grad school, maybe before my PhD.
Two or three years.

**Tell me what else you remember from your early time in the community.**
**Who else was there, and what were the big discussions?**

Back then it was early 2.x days -- just after 2.2 came out, or maybe 2.1.
Who was there? Martin [von Löwis], Neil Norwitz, Marc-André [Lemburg],
Andrew Kuchling, Alex Martelli, Tim [Peters], Jeremy [Hylton]. All the originals.
Raymond [Hettinger] was there. Greg [Stein] was there. Jack [Jansen] was
around still. It was still a small group. I got involved just before the first
PyCon US in DC, 2003. I remember going to that and meeting everybody in the
sprint room. Barry [Warsaw] was there, obviously. It was still a time when a lot of
people just didn't know the language at all, or it was just "oh, that language
with the whitespace." It was small enough that it was all impassioned hobbyists.
A lot of us maybe used it at work, a lot of us didn't at all.

**I was very much the impassioned hobbyist myself.**

Exactly. It was still small enough that if you wanted to make a change, you just
did it. If you needed help, you just asked. The discussions never got too huge
-- they got big sometimes, but we had PEPs by then.

**I think Barry started the PEPs almost as soon as we left CNRI.**

I think you came up with that while you were at BeOpen, just prior to all this.

**Do you remember Ping?**

[Ka-]Ping [Yee] was definitely active. He got up at PyCon and told me he didn't
like me getting rid of tuple unpacking in parameters.

**That came up in Python 3. I was in favor of removing it.**

I asked you if I could do it. It came up in 2007 when PyCon US was in Texas.
Ping got up to a microphone and said, don't take it out. He was definitely
active back then with pydoc and cgitb.

**Inspect was his too. And he was involved in the redesign of exceptions --**
**the chaining, "this exception happened during the handling of that one."**

Yep. He'd really thought through the different needs carefully.

**I should invite him for an interview too. We're still friends.**

That'd be fun. But yeah, back then the team was just smaller. It felt a bit
easier-going. We were never a hundred core devs at that point -- maybe 50, and
probably half weren't active. The number of us considered active was in the
twenties.

**We have more active people now.**

I remember for a long time I kept track of it as a way to try to poke companies
to let people be more active at work. Like, please let your employees who are
core devs do more because we only have so many active. Or donate to the PSF so
someday we might be able to hire people, like we finally do now to help
contribute consistently, because a lot of us just didn't get work time.

**Yeah, we have at least four developers-in-residence now.**
**There's Łukasz, Petr, Serhiy, and Seth, the security guy.**

Security engineer in residence.
They don't call Seth a developer-in-residence from the PSF perspective because
he's funded through the Alpha-Omega project -- a security initiative with Google
and other companies trying to improve security of important open source
projects. They donate to the PSF to cover Seth. But back then it was
atypical to get to work on Python as part of your job. Almost all volunteer
time, spare time. Not all of us even got to use Python at work. Just a lot of
passionate users.

**Still happens.**

Still happens. Anyway, PyCon US -- that's when I got into the PSF without
knowing it. Someone nominated me and I didn't know. The day after the vote,
everyone came up to me at PyCon and said, congratulations. I said, for what?
They said, you got elected to the PSF. I didn't even know I'd been nominated.

**And that was when the PSF had like 30 members?**
**Every new member had to be approved by the existing members.**

It was tiny. The next year, 2004, my first PSF meeting in person, we all just
sat at a couple of tables in DC.

**Not exactly a diversity-encouraging way of doing it.**

No. And then shortly after that PyCon I got my commit bit. I said I
could fix something but needed someone to commit it. You said, "Oh, you don't
have commit rights yet?" I think Raymond logged into SourceForge and clicked the
button. I made my first commit on April 18th, 2003.

**We were still on SourceForge? Using CVS?**

Yes, Martin hadn't moved us to Subversion yet. Martin got us to Subversion, then
I got us from Subversion to Mercurial, Mercurial to Git, SourceForge to Roundup,
and Roundup to GitHub.

**That was in the early days when SourceForge was not yet a pool of evil.**

It was the only place doing open source hosting. I also have random scattered
memories, like Daniel Berlin being involved.

**Who's Daniel Berlin again?**
**He had a law degree and a computer science degree?**

He was a lawyer at Google. He was on the mailing list and one time talked about
wishing there was a way to make the `thread` and `threading` modules work on
non-threaded builds. I ended up creating the `dummy_thread` and
`dummy_threading` modules as a shim, based on his idea. He didn't have the time,
but it was during my gap year so I did. Those were my first standalone modules
in the standard library.

**He was never a core dev, though -- just on python-dev.**

Exactly, he occasionally came up with ideas.

**Who else was very vocal?**

Marc-André was vocal. I think PJE [Phillip J. Eby] was around by then too.
Martin, obviously.

**Martin was much more centrally important,**
**but PJ also did some amazing stuff for the community.**

I started to pick up on people's coding styles. That's how I knew Ping wrote
`inspect` -- I had to edit some code and recognized his style.

**How do you recognize Ping's style?**

It was just the way it was structured. Not overly complicated, but distinctive.
I can't articulate it exactly anymore -- that was during my PhD, when I was
working on importlib. And PJ was somewhat similar in terms of complexity. He was
prolific, but the level of flexibility he built was taken to an extreme, in my
opinion.

**I'm always reluctant to make everything extensible.**
**My goal is not to be prepared for everything the future could possibly bring,**
**because the future always brings something unexpected.**

Exactly. There's no way to nail it.

**Do you remember when Raymond Hettinger started?**

He started about a year before me -- got his commit bit in 2002, I got mine in
2003. Then there was Python 3: helping write PEP 3000 with Andrew Kuchling,
which later became PEP 3100 when we took PEP 3000 over for the motivation. And
then the gutting of the standard library.

**PEP 3100 was the miscellaneous Python 3 features --**
**a big list of little things.**
**Some of them would have been worth a PEP by themselves.**

Andrew originally started that PEP, and I helped so much he made me co-author. I
don't know if he made it to the end -- it was a long process. Fred Drake and I
had an unofficial competition over who could delete more lines from the standard
library in the 2-to-3 transition. I got to delete the `compiler` package, so I
think I won.

**Where did the compiler package come from?**

That predates me. We decided to get rid of it because it didn't keep up. We had
the new compiler that Jeremy started, and you gave a deadline to get it finished
at PyCon in Texas, maybe 2006. I jumped in to help, and that's when we got the
AST finished in time. But the `compiler` package never kept up, so we eventually
added the `ast` module to replace it.

**What was the point of the compiler package?**

I think it was a pure Python way to work with the syntax tree and customize
bytecode emission -- because we didn't expose the internals and there was no
`ast` module yet. But I don't honestly remember the details. We just got tired
of having to implement everything twice: once for the interpreter and once for
that package.

**That's still a scar we carry --**
**modules with both a C implementation and a Python implementation.**
**The Python version is often only used by PyPy.**

Right, and that's my fault -- the accelerator PEP. I wrote it to say: if you're
writing an accelerator module in C, you must have a pure Python reference
version so other implementations can work from it. At the time it made sense
because there were Jython, IronPython, and PyPy all trying to re-implement the
standard library from scratch. But with IronPython and Jython not making the
jump to Python 3, it's now mostly just us and PyPy. I won't call it dead weight,
but it is somewhat of a burden.

**I think the PEP was a good idea at the time.**
**It was an improvement over the pattern where**
**`profile` and `cProfile` had *subtly different APIs.**

Definitely. But that's more of a future-of-Python thing. It's a good
reminder that I wrote that PEP way back when.

**Often PEPs were written based on some idea I had.**

Sometimes. It was a mix -- sometimes you had an idea and someone would write it
up, sometimes people came up with their own ideas.

**The worst is when PEPs are proposed by people completely outside the**
**community. Those almost never have a chance.**

That's why we introduced PEP sponsors. And that's also why Titus Brown and I
created python-ideas -- as a filter for python-dev, because we were getting so
many half-baked proposals.

**What do you remember of Titus Brown?**

Titus is a professor in evolutionary biology, using Python extensively in the
sciences. He was an avid community member, really big in the testing side of
things. He and I started python-ideas together. That was when we were trying to
improve the signal-to-noise ratio on python-dev. Then python-ideas itself got
rowdy, and we had to introduce a code of conduct for the first time.

**Was python-ideas the first mailing list with a code of conduct?**

I think so. After the PSF created one, we adopted it immediately. This was back
when you had to justify having a code of conduct at all.

**A lot of people were against them.**

There was a lot of lack of understanding about why they existed. People feared
it would be weaponized against them. But we said: the purpose is to protect
people and make them feel comfortable. If we abuse it, you can complain to the
PSF and get us removed as list admins. Eventually people calmed down when they
saw it was only used against genuinely poor participants.

**Even then there was fear of wokeness, not by that name.**

Not by that name, no. But yes.

**If you go to the actual archives and try to fact-check,**
**everything is completely different from what you remember.**

I got dates wrong in the documentary, right? I said the wrong year for my
internship with you -- I knew it crossed a calendar boundary from fall into
winter, but I said I ended in '08 when I actually started in '08.

**How was that internship for you?**

It was fun. That was the App Engine team. I came and joined the team full-time
after that. It was great to hang out with you and the rest of the team in SF. On
a personal note, that was the winter after my girlfriend left me and then
committed suicide. I was still recovering, so it was good to get out of
Vancouver and change the scene.

**Was that before you met Andrea?**

I met Andrea in May 2009, after the internship. I went back to school for a
couple of months and we met playing softball. What else... The whole 2-to-3
transition. Importlib and the import system -- my rewrite of it, bootstrapping
Python code into core parts of the interpreter. And when I graduated I worked
for the PSF for two months to write the dev guide.

**Did you write the dev guide from scratch?**

From scratch. It was nowhere near what it is now -- much smaller. I finished my
PhD in February 2011, had two months before starting at Google, and was a
contractor with the PSF during that time.

**That's a lot of important work.**

I wrote it all down for a EuroPython talk and it was weird to see the length of
the bullet lists. Then again, I've been doing this for 22 years. Not half my
life yet -- I think October 2027 is when I hit the midway point.

**I'm about at the midway point myself --**
**I started Python around 1990, when I turned 34.**

I got my commit bit in April 2003, before I turned 25. I'm turning 47 now.

**It's been a fun ride.**
**I'm guessing some of it has been stressful for you too.**

Well, that's covered in the documentary -- your retirement and the voting thing.

**You admitted how stressful it was for you.**
**I'd never anticipated it would cause anyone stress**
**because I was so focused on my own situation.**

My positioning around conduct and calling out bad behavior meant people came to
me with their problems. I've had points of stress because people shared their
own stressful situations -- usually interpersonal issues on the team. Plus
enforcing the code of conduct on python-ideas, -discuss, and elsewhere. I've been
on the conduct working group for the PSF. I've always taken it as a way of
giving back, because I found python-dev so welcoming and wanted to help keep it
that way. Now I want it to be welcoming enough that if my own child decides to
get involved, I can say: go for it, no qualms.

The retirement and choosing-how-to-choose period was hard because there was no
guarantee we'd get our acts together. There were some very strong personalities
with very strong opinions, and getting everyone aligned took a lot of convincing
-- what I call soft power. Those of us who'd been on the team a while tried to
say: let's organize and get this done, let's not butt heads. But there was so
much arguing over minutiae.

**There were five competing PEPs with different governance proposals.**

Honestly, the competing PEPs were fine. The stressful part was the voting
system. Once we knew how we were going to select, everyone just wrote down ideas
and we voted. Whatever won, won.

**Nobody objected to the way the vote was held?**

In the end, no. But figuring out *how* to vote was the hard part.

**Voting for what I think of as the constitution?**

Voting for the constitution. Do you remember, you emailed me and Barry about how
frustrated you were? There was a day you were getting on Caltrain to go to work
and you emailed us saying: I'm really frustrated, maybe I should just name Brett
BDFL. Then you got on the train. By the time you got to work, you'd calmed down
and said: let's see if everyone can work it out. So apparently for two hours I
was potentially going to be the BDFL.

**What were the points of disagreement?**

We literally could not decide how to vote. We could not decide how to decide.
First-past-the-post or approval voting? Anonymity? We quickly agreed to use PEPs
for the proposals, but the voting mechanism was constant back and forth. The
real problem was: since you'd said it was all up to us, there was no way to make
a final decision. We had to all implicitly agree, but there was no mechanism to
end the debate.

**That was kind of my intention.**

I knew it was. But it made things hard because there was no way for us to say
"OK, we've decided" -- it had to be all of us somehow deciding we'd agreed
enough.

**There had to be a schedule, an administrator for the election.**
**It wasn't about whether someone voted twice --**
**it was about when are we ready, what are we voting on, what voting system.**

Exactly. Those of us with some standing were trying to exert soft power, coaxing
everyone toward a resolution. You can't vote on how you're going to vote --

**You get an infinite regression.**

Exactly. And if someone disagrees, at what point do you care? If Barry doesn't
like it, that's different from someone who just became a core dev. There was no
way to have a definitive "we're done" -- it had to be a nebulous sense that
there wasn't enough loud complaining. I don't know if it was exhaustion or if we
finally realized we needed to finish because people were watching. But we got it
done.

**I can see that bickering stresses you out**
**more than it stresses the bickerers themselves.**

Probably. And I didn't want to see the project go away. I have enough friends
here that it would be really sad if we couldn't hang out anymore just because
the project dissolved.

**It never occurred to me that Python could die.**
**By 2018 it was already in the top 10, if not top 5, of programming languages.**

It's not that the software would go away. It was more about what would happen to
the development team if we seriously couldn't agree.

**I think that was stressing me out too. But it worked out.**

We got the steering council. You and I did it the first time, I did it four more
times, and it seems to have worked out.

**I'd like to see term limits of five years.**
**We've sort of accidentally always had that.**

I advocated for five or ten originally but got shot down. That's why I stuck to
five when I stepped down -- partly because I knew I was going to be a parent,
partly to stick by my word. I still think it's a good idea. Thomas accidentally
helped keep the trend going. We'll have to see what Pablo does -- I think he's
next at five years. Barry's time is harder to count since he took a break.

**I think term limits should be cumulative, like US presidents --**
**total years served, not contiguous.**

I support that too. It might be worth proposing.

**If you wanted to propose it, I'd be happy to see that.**
**I don't think it would be very controversial.**

It's one of those political-system things. Maybe because we've done it long
enough now, people will accept it. We'd need to change PEP 13.

**I think the way to change PEP 13 is just a vote.**
**I introduced STAR voting -- that wasn't a PEP, just a vote on Discourse.**

Right. I guess I'd just propose it, and if there's general agreement, open a
poll for two weeks in the committers category.

**You have to make sure only committers can vote**
**and results aren't revealed until after voting closes.**

If I'm going to do it, probably next month, so it's well before we call for
nominees.

**It's mid-September. There's plenty of time.**

I can do that. No big deal.

**[Brett didn't propose it. In December 2025**
**Thomas Wouters was elected for a 6th term, after a one-year gap. --Guido]**
