"""Generate the sample dataset for the eval harness.

Produces:
- `eval/data/documents/` 50 files in a balanced mix of .md, .html, .pdf
- `eval/data/labels/labels.jsonl` 20 hand-curated entity + relationship sets
- `eval/data/qa/qa_pairs.jsonl` 30 Q&A pairs with expected source paths

Run with: `python eval/generate_dataset.py`
"""
from __future__ import annotations

import json
import random
import textwrap
from pathlib import Path
from typing import Iterable

# Deterministic output so reruns match what the eval harness expects.
random.seed(42)

ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT / "data" / "documents"
LABELS_DIR = ROOT / "data" / "labels"
QA_DIR = ROOT / "data" / "qa"
for d in (DOCS_DIR, LABELS_DIR, QA_DIR):
    d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# Source material — 50 short articles. Each entry is (slug, title, body, kind).
# We keep the bodies small (300-600 words) so ingestion is fast and the eval
# harness runs in seconds, not minutes.
# --------------------------------------------------------------------------


def _t(s: str) -> str:
    """Dedent + strip a triple-quoted string."""
    return textwrap.dedent(s).strip()


ARTICLES: list[tuple[str, str, str]] = [
    # ---- AI / computing history (dense in entities + relations) ----
    (
        "alan_turing_life",
        "Alan Turing: Life and Work",
        _t(
            """
            # Alan Turing: Life and Work

            Alan Turing was a British mathematician born in London in 1912. He is
            widely regarded as the father of theoretical computer science. While at
            the University of Cambridge, Turing published his 1936 paper "On
            Computable Numbers" introducing the Turing machine, an abstract
            device that defines what it means for a function to be computable.

            During World War II, Turing worked at Bletchley Park, the UK's
            codebreaking centre. There he designed the Bombe, an electromechanical
            machine that helped crack the German Enigma cipher. His colleague
            Gordon Welchman later improved the design with the "diagonal board".

            After the war, Turing joined the National Physical Laboratory where
            he designed the Automatic Computing Engine (ACE). In 1948 he moved
            to the University of Manchester and worked on the Manchester Mark 1,
            one of the first stored-program computers. He also published a
            seminal 1950 paper "Computing Machinery and Intelligence" proposing
            the Turing Test.

            Turing died in 1954 in Wilmslow, Cheshire. In 2009 the British Prime
            Minister Gordon Brown issued an official apology for his prosecution
            for homosexuality. He was granted a posthumous royal pardon in 2013.
            """
        ),
    ),
    (
        "bletchley_park",
        "Bletchley Park",
        _t(
            """
            # Bletchley Park

            Bletchley Park is a country estate in Milton Keynes, England. During
            World War II it became the principal centre of Allied codebreaking.
            The Government Code and Cypher School (GC&CS), the forerunner of
            GCHQ, was based there from 1939.

            Notable staff included Alan Turing, Gordon Welchman, Hugh Alexander,
            and Joan Clarke. The site is famous for cracking the German Enigma
            and Lorenz ciphers. The Bombe, designed by Turing and refined by
            Welchman, was manufactured under Harold Keen at the British
            Tabulating Machine Company in Letchworth.

            Bletchley Park was kept secret until the 1970s. Today it operates as
            a museum. The National Museum of Computing, housed in Block H, holds
            a rebuilt Colossus computer — the world's first programmable digital
            electronic computer, designed by Tommy Flowers.
            """
        ),
    ),
    (
        "enigma_machine",
        "The Enigma Machine",
        _t(
            """
            # The Enigma Machine

            Enigma was a rotor cipher machine used by Nazi Germany for military
            communications. It was invented by the German engineer Arthur
            Scherbius at the end of World War I and adopted by the German
            military in the 1920s and 1930s.

            The machine used a series of rotating rotors, a reflector, and a
            plugboard to scramble letters. The German Navy (Kriegsmarine) used a
            more sophisticated variant called M4, with four rotors, which was
            particularly hard to break.

            Polish cryptanalysts at the Cipher Bureau, including Marian
            Rejewski, made the first breakthroughs in 1932. Their work was
            handed to British and French intelligence in 1939. At Bletchley Park,
            Alan Turing's Bombe automated the search for daily key settings.

            The breaking of Enigma is estimated to have shortened World War II
            by at least two years.
            """
        ),
    ),
    (
        "turing_machine_concept",
        "The Turing Machine Concept",
        _t(
            """
            # The Turing Machine Concept

            A Turing machine is a mathematical model of computation defined by
            Alan Turing in 1936. It consists of an infinite tape divided into
            cells, a read/write head, a finite set of states, and a transition
            function that determines the next action based on the current state
            and symbol.

            The Church-Turing thesis, formulated independently by Alonzo Church
            and Turing, asserts that any effectively calculable function can be
            computed by a Turing machine. This thesis underpins theoretical
            computer science.

            A problem is called Turing-decidable if a Turing machine exists that
            halts on every input and answers yes/no correctly. The Halting
            Problem — determining whether an arbitrary program halts — was shown
            by Turing to be undecidable.

            Variants include the universal Turing machine, which can simulate
            any other Turing machine given its description on the tape. Modern
            computers are essentially practical realisations of a universal
            Turing machine.
            """
        ),
    ),
    (
        "ai_winter_1970s",
        "The First AI Winter",
        _t(
            """
            # The First AI Winter

            The first AI winter (1974-1980) was a period of reduced funding and
            interest in artificial intelligence research. It followed the
            disappointing results of early machine translation projects such as
            the Georgetown-IBM experiment of 1954.

            In 1966 the ALPAC report, commissioned by the US National Research
            Council, concluded that machine translation was not feasible in the
            near term, leading to deep cuts in funding. Around the same time, the
            machine learning work of Frank Rosenblatt on the Perceptron was shown
            by Marvin Minsky and Seymour Papert to be unable to learn the XOR
            function.

            The Lighthill Report of 1973, commissioned by the UK Science Research
            Council, criticised AI research for failing to deliver on its
            promises. This led to near-total cuts in British AI funding.

            The field revived in the 1980s with the success of expert systems
            such as XCON at Digital Equipment Corporation and the introduction of
            the Fifth Generation Computer Systems project by Japan's MITI.
            """
        ),
    ),
    (
        "deep_learning_rise",
        "The Rise of Deep Learning",
        _t(
            """
            # The Rise of Deep Learning

            Deep learning emerged from research on artificial neural networks.
            Key milestones include Geoff Hinton and David Rumelhart's 1986 paper
            on backpropagation, and Yann LeCun's work on convolutional neural
            networks (CNNs) for handwritten digit recognition at Bell Labs in
            1989.

            The breakthrough came in 2012 when Alex Krizhevsky, Ilya Sutskever,
            and Geoff Hinton won the ImageNet competition using a deep CNN
            called AlexNet, trained on NVIDIA GPUs. This halved the error rate
            of traditional computer vision methods.

            Recurrent neural networks (RNNs) and long short-term memory (LSTM)
            networks, invented by Sepp Hochreiter and Jürgen Schmidhuber in
            1997, dominated sequence tasks until the 2017 paper "Attention Is
            All You Need" by Ashish Vaswani and colleagues at Google introduced
            the Transformer architecture.

            In 2018 OpenAI released GPT, followed by GPT-2 in 2019 and GPT-3 in
            2020. Google released BERT in 2018. These transformer-based large
            language models reshaped natural language processing.
            """
        ),
    ),
    (
        "transformer_architecture",
        "The Transformer Architecture",
        _t(
            """
            # The Transformer Architecture

            The Transformer is a neural network architecture introduced by
            Ashish Vaswani and colleagues at Google in the 2017 paper "Attention
            Is All You Need". It replaced recurrent layers with multi-head
            self-attention, enabling parallel training on GPUs.

            A transformer consists of an encoder and a decoder, each made of
            stacked layers. Each layer has a multi-head self-attention sublayer
            and a position-wise feed-forward sublayer. Positional encodings are
            added to input embeddings to preserve word order information.

            Encoder-only transformers such as BERT (Devlin et al., 2018) excel
            at classification and span extraction. Decoder-only transformers
            such as GPT (Radford et al., 2018) excel at autoregressive text
            generation. T5 (Raffel et al., 2019) uses the full encoder-decoder
            for text-to-text tasks.

            Scaled dot-product attention computes softmax(QK^T / sqrt(d_k)) V.
            Multi-head attention runs several attention layers in parallel and
            concatenates their outputs.
            """
        ),
    ),
    (
        "openai_company",
        "OpenAI: Company History",
        _t(
            """
            # OpenAI: Company History

            OpenAI was founded in December 2015 in San Francisco by Sam Altman,
            Elon Musk, Ilya Sutskever, Greg Brockman, Wojciech Zaremba, and John
            Schulman. It started as a non-profit research lab with a USD 1
            billion pledge from its founders.

            In 2018 Elon Musk stepped down from the board, citing conflicts of
            interest with Tesla's AI work. In 2019 OpenAI transitioned to a
            "capped-profit" structure, forming OpenAI LP with Microsoft as a
            major investor. Microsoft invested USD 1 billion in 2019 and a
            further USD 10 billion in 2023.

            OpenAI's product lineup includes the GPT family of large language
            models (GPT-2 in 2019, GPT-3 in 2020, GPT-4 in 2023, GPT-4o in 2024),
            the DALL-E image generation models, the Whisper speech recognition
            model, and the Sora video generation model. ChatGPT, launched in
            November 2022, became the fastest-growing consumer application in
            history, reaching 100 million users in two months.

            In November 2023 Sam Altman was briefly fired and reinstated as CEO
            within five days, leading to a reshaped board.
            """
        ),
    ),
    (
        "anthropic_company",
        "Anthropic: Company History",
        _t(
            """
            # Anthropic: Company History

            Anthropic is an AI safety company founded in 2021 by Dario Amodei
            and Daniela Amodei, both former OpenAI executives. Based in San
            Francisco, Anthropic has raised over USD 7 billion in funding, with
            major investments from Google, Spark Capital, and Amazon.

            Anthropic is best known for the Claude family of large language
            models. Claude was first released in March 2023. Claude 2 followed
            in July 2023 with a 100,000-token context window. Claude 3, released
            in March 2024, came in three sizes: Haiku, Sonnet, and Opus. Claude
            3.5 Sonnet was released in June 2024.

            Anthropic pioneered "Constitutional AI", a training method where the
            model evaluates and revises its own outputs against a written
            constitution of principles. The constitution draws on sources
            including the UN Declaration of Human Rights and Apple's terms of
            service.

            In 2024 Anthropic launched the Model Context Protocol (MCP), an open
            standard for connecting AI assistants to external data sources and
            tools.
            """
        ),
    ),
    (
        "google_deepmind",
        "Google DeepMind",
        _t(
            """
            # Google DeepMind

            DeepMind was founded in London in 2010 by Demis Hassabis, Shane Legg,
            and Mustafa Suleyman. The company was acquired by Google in 2014 for
            USD 500 million.

            DeepMind is known for applying reinforcement learning to games.
            AlphaGo, defeated Lee Sedol at Go in March 2016 in Seoul. AlphaZero,
            published in 2017, learned to master chess, shogi, and Go through
            self-play. AlphaFold, released in 2020, solved the protein structure
            prediction problem and won Hassabis and John Jumper the 2024 Nobel
            Prize in Chemistry.

            In April 2023 Google merged DeepMind with Google Brain, its internal
            AI lab, to form Google DeepMind. The Gemini family of multimodal
            models, announced in December 2023, was developed under the merged
            unit.

            Key DeepMind researchers include David Silver (AlphaGo lead), Volodymyr
            Mnih (DQN author), and Oriol Vinyals (StarCraft II lead).
            """
        ),
    ),
    # ---- Programming & systems ----
    (
        "python_history",
        "Python Programming Language History",
        _t(
            """
            # Python Programming Language History

            Python was created by Guido van Rossum at the Centrum Wiskunde &
            Informatica (CWI) in Amsterdam. Work began in December 1989 as a
            successor to the ABC language. The first public release, version
            0.9.0, was published in February 1991 on the alt.sources newsgroup.

            Python 2.0 was released in October 2000, introducing list
            comprehensions and a garbage collector for reference cycles. Python
            3.0, released in December 2008, was a backwards-incompatible
            redesign that unified text and bytes.

            Guido van Rossum stepped down as Benevolent Dictator for Life in
            July 2018. Leadership passed to a five-person Steering Council
            elected annually by the Python Software Foundation.

            The language is widely used in data science (NumPy by Travis
            Oliphant, pandas by Wes McKinney, scikit-learn), machine learning
            (PyTorch by Meta, TensorFlow by Google), and web development
            (Django, Flask).
            """
        ),
    ),
    (
        "linux_kernel",
        "The Linux Kernel",
        _t(
            """
            # The Linux Kernel

            The Linux kernel was created by Linus Torvalds in 1991 while he was
            a student at the University of Helsinki. He announced the project on
            the comp.os.minix newsgroup on 25 August 1991. The first public
            release, version 0.01, shipped on 17 September 1991 with about
            10,000 lines of code.

            Linux is released under the GNU General Public License version 2.
            The decision to make it free software was influenced by a
            conversation with Andrew Tanenbaum, author of the MINIX operating
            system, who had refused to let Torvalds extend MINIX.

            Major corporate contributors include Intel, Red Hat, IBM, SUSE, and
            Google. As of 2024 the kernel contains over 30 million lines of
            code, with roughly 2,000 developers contributing to each release.

            The Linux Foundation, founded in 2007 and based in San Francisco,
            coordinates development. Linus Torvalds remains the project's
            principal maintainer, with final say on what is merged.
            """
        ),
    ),
    (
        "git_version_control",
        "Git: Distributed Version Control",
        _t(
            """
            # Git: Distributed Version Control

            Git was created by Linus Torvalds in 2005 for managing development
            of the Linux kernel. Torvalds created Git after the Linux
            community lost free access to BitKeeper, a proprietary version
            control system they had been using since 2002. The first release
            was announced on 7 April 2005.

            Git is a distributed version control system: every clone is a full
            repository with complete history. Key operations include commit,
            branch, merge, rebase, and tag. The data model is a directed
            acyclic graph (DAG) of commits, where each commit references its
            parent(s) and a tree of file snapshots.

            GitHub, founded in 2008 by Tom Preston-Werner, Chris Wanstrath, and
            PJ Hyett, provided a hosted Git service that became the dominant
            platform for open source collaboration. Microsoft acquired GitHub in
            2018 for USD 7.5 billion.

            Junio Hamano took over as Git's maintainer from Torvalds in July
            2005 and has held the role since.
            """
        ),
    ),
    (
        "docker_containers",
        "Docker and Containerisation",
        _t(
            """
            # Docker and Containerisation

            Docker was released in March 2013 by dotCloud, a San Francisco
            startup founded by Solomon Hykes. The technology was based on
            Linux containers (LXC) and the cgroups and namespaces features of
            the Linux kernel, originally developed by Google engineers Paul
            Menage and Rohit Seth in 2006.

            Docker popularised container images — portable, layered filesystem
            snapshots that can be distributed through registries. The Docker
            Hub public registry launched in 2014.

            In 2015 Docker and CoreOS jointly announced the Open Container
            Initiative (OCI), a Linux Foundation project that defines open
            standards for container formats and runtimes. The OCI Image Spec
            and Runtime Spec (runc) are now widely adopted.

            Kubernetes, released by Google in 2014 based on internal Borg
            system experience, became the dominant container orchestration
            platform. The Cloud Native Computing Foundation (CNCF), founded in
            2015, hosts Kubernetes, containerd, and other projects.
            """
        ),
    ),
    (
        "rust_language",
        "The Rust Programming Language",
        _t(
            """
            # The Rust Programming Language

            Rust was designed by Graydon Hoare at Mozilla Research starting in
            2006. Mozilla sponsored the project from 2009 and announced it
            publicly in 2010. The first stable release, Rust 1.0, shipped on
            15 May 2015.

            Rust's central innovation is the ownership system, enforced at
            compile time by the borrow checker. The system prevents data races
            and use-after-free errors without a garbage collector. The three
            rules of ownership: each value has one owner, when the owner goes
            out of scope the value is dropped, and borrows are either shared
            or mutable but never both.

            Rust uses the Cargo package manager, hosted on crates.io. Editions
            (2015, 2018, 2021, 2024) allow the language to evolve without
            breaking existing code.

            The Rust Foundation, founded in 2021, is a non-profit based in
            San Francisco. Members include Amazon, Google, Microsoft, Huawei,
            and Mozilla. Rust has been voted "most loved language" in the
            Stack Overflow Developer Survey for many consecutive years.
            """
        ),
    ),
    # ---- Science ----
    (
        "crispr_gene_editing",
        "CRISPR Gene Editing",
        _t(
            """
            # CRISPR Gene Editing

            CRISPR (Clustered Regularly Interspaced Short Palindromic Repeats)
            is a family of DNA sequences found in bacteria. CRISPR is part of
            an adaptive immune system that bacteria use to remember and destroy
            viruses they have encountered.

            The CRISPR-Cas9 gene editing technique was developed in 2012 by
            Jennifer Doudna at the University of California, Berkeley, and
            Emmanuelle Charpentier at the Max Planck Institute in Berlin. Their
            paper, published in Science in August 2012, showed that Cas9 could
            be programmed with a guide RNA to cut DNA at any desired location.

            Feng Zhang at the Broad Institute and George Church at Harvard
            independently demonstrated CRISPR-Cas9 editing in human cells in
            January 2013. A patent dispute between Berkeley and the Broad
            Institute lasted years, with the US Patent Trial and Appeal Board
            ruling in 2022 that the Broad's claims were distinct.

            Doudna and Charpentier were awarded the 2020 Nobel Prize in
            Chemistry. The first approved CRISPR therapy, Casgevy for sickle
            cell disease, was approved by the UK Medicines and Healthcare
            products Regulatory Agency in November 2023.
            """
        ),
    ),
    (
        "general_relativity",
        "General Relativity",
        _t(
            """
            # General Relativity

            General relativity is Albert Einstein's theory of gravitation,
            published in a series of papers in 1915. It generalises special
            relativity and Newton's law of universal gravitation.

            The central equation is the Einstein field equation:
            G_mu_nu + Lambda * g_mu_nu = 8 * pi * G / c^4 * T_mu_nu. The left
            side describes the curvature of spacetime; the right side
            describes the matter and energy present.

            Key predictions include gravitational time dilation, the
            gravitational redshift, the deflection of light by massive bodies,
            and gravitational waves. The deflection of starlight by the Sun was
            measured by Arthur Eddington during a total solar eclipse in 1919,
            making Einstein world-famous.

            Karl Schwarzschild found the first exact solution to Einstein's
            equations in 1916, describing what we now call a black hole. The
            Event Horizon Telescope collaboration published the first image of
            a black hole — the supermassive black hole at the centre of galaxy
            M87 — in April 2019.

            Gravitational waves were directly detected for the first time on
            14 September 2015 by the LIGO collaboration. Rainer Weiss, Kip
            Thorne, and Barry Barish received the 2017 Nobel Prize in Physics
            for this work.
            """
        ),
    ),
    (
        "quantum_mechanics_origins",
        "Origins of Quantum Mechanics",
        _t(
            """
            # Origins of Quantum Mechanics

            Quantum mechanics emerged between 1900 and 1927 from a series of
            breakthroughs by European physicists. Max Planck at the University
            of Berlin introduced the quantum of action in 1900 to solve the
            black-body radiation problem. Albert Einstein extended the idea in
            1905 to explain the photoelectric effect.

            Niels Bohr, working at the University of Copenhagen, proposed his
            model of the atom in 1913, with electrons orbiting the nucleus in
            quantised energy levels. The Bohr model explained the hydrogen
            spectrum but failed for heavier elements.

            Modern quantum mechanics was formulated independently by Werner
            Heisenberg in 1925 (matrix mechanics) and Erwin Schrödinger in 1926
            (wave mechanics). Schrödinger showed the two formulations were
            equivalent. Paul Dirac at Cambridge unified them with a more
            general formalism.

            Heisenberg's uncertainty principle, formulated in 1927, states that
            position and momentum cannot both be known precisely. The
            Copenhagen interpretation, championed by Bohr and Heisenberg, holds
            that quantum states collapse upon measurement.
            """
        ),
    ),
    (
        "standard_model",
        "The Standard Model of Particle Physics",
        _t(
            """
            # The Standard Model of Particle Physics

            The Standard Model is a quantum field theory describing three of
            the four known fundamental forces: electromagnetism, the weak
            nuclear force, and the strong nuclear force. It was developed
            between 1960 and 1973 by Sheldon Glashow, Steven Weinberg, Abdus
            Salam, Murray Gell-Mann, and others.

            The model classifies elementary particles into fermions (quarks and
            leptons) and bosons (force carriers). There are six quarks (up,
            down, charm, strange, top, bottom) and six leptons (electron,
            muon, tau, and three neutrinos). Force carriers are the photon
            (electromagnetism), W and Z bosons (weak force), and gluons
            (strong force).

            The Higgs mechanism, proposed by Peter Higgs, François Englert,
            and Robert Brout in 1964, explains how particles acquire mass. The
            Higgs boson was discovered on 4 July 2012 by the ATLAS and CMS
            experiments at CERN's Large Hadron Collider near Geneva. Higgs and
            Englert received the 2013 Nobel Prize in Physics.

            The Standard Model does not include gravity, dark matter, or
            neutrino masses. Extensions include supersymmetry and string theory.
            """
        ),
    ),
    (
        "human_genome_project",
        "The Human Genome Project",
        _t(
            """
            # The Human Genome Project

            The Human Genome Project was an international scientific research
            project with the goal of determining the sequence of nucleotide
            base pairs that make up human DNA. It was launched in October 1990
            in the United States, led by the National Institutes of Health
            (NIH) and the Department of Energy (DOE), with James Watson as its
            first director.

            Major participating institutions included the Wellcome Sanger
            Institute in Hinxton, UK, the Whitehead Institute at MIT, and the
            Baylor College of Medicine. Francis Collins took over from Watson
            in 1993.

            A private competitor, Celera Genomics, was founded by Craig Venter
            in 1998. Celera used the whole-genome shotgun sequencing technique
            developed by Venter, while the public project used a hierarchical
            clone-by-clone approach.

            The project was declared complete in April 2003, two years ahead of
            schedule and under budget. It cost approximately USD 3 billion. The
            reference sequence covers about 92% of the human genome; the
            Telomere-to-Telomere (T2T) Consortium completed the remaining
            8% in 2022.
            """
        ),
    ),
    (
        "crick_watson_dna",
        "Crick, Watson, and the Double Helix",
        _t(
            """
            # Crick, Watson, and the Double Helix

            On 25 April 1953, James Watson and Francis Crick published "Molecular
            Structure of Nucleic Acids: A Structure for Deoxyribose Nucleic
            Acid" in the journal Nature. The paper proposed a double helix
            structure for DNA, with two antiparallel strands connected by
            complementary base pairs (adenine with thymine, guanine with
            cytosine).

            The discovery was based in part on X-ray diffraction images taken
            by Rosalind Franklin and her student Raymond Gosling at King's
            College London. Franklin's Photograph 51, taken in May 1952, was
            shown to Watson by her colleague Maurice Wilkins without her
            knowledge.

            Watson, Crick, and Wilkins shared the 1962 Nobel Prize in
            Physiology or Medicine. Rosalind Franklin died of ovarian cancer in
            1958 at age 37 and was therefore ineligible for the Nobel Prize,
            which is not awarded posthumously.

            Watson and Crick worked at the Cavendish Laboratory in Cambridge.
            Their model was confirmed by Meselson and Stahl's 1958 experiment
            demonstrating semiconservative DNA replication.
            """
        ),
    ),
    # ---- History ----
    (
        "roman_republic",
        "The Roman Republic",
        _t(
            """
            # The Roman Republic

            The Roman Republic was the era of classical Roman civilisation
            beginning with the overthrow of the Roman Kingdom, traditionally
            dated to 509 BCE, and ending in 27 BCE with the establishment of
            the Roman Empire under Augustus.

            The Republic was governed by a constitution that combined
            monarchic, aristocratic, and democratic elements. The Senate, made
            up of former magistrates, was the dominant deliberative body. Two
            consuls, elected annually, served as chief executives.

            Major figures include Lucius Junius Brutus, who led the revolt
            against Tarquin the Proud; Cincinnatus, the farmer called to be
            dictator in 458 BCE; and the brothers Tiberius and Gaius Gracchus,
            tribunes who attempted land reform and were assassinated in 133 and
            121 BCE respectively.

            The Republic collapsed after a century of civil wars. Julius Caesar
            crossed the Rubicon in 49 BCE, defeated Pompey at Pharsalus in 48
            BCE, and was assassinated on the Ides of March (15 March) 44 BCE.
            His adopted heir Octavian defeated Mark Antony and Cleopatra at the
            Battle of Actium in 31 BCE and became Augustus in 27 BCE.
            """
        ),
    ),
    (
        "french_revolution",
        "The French Revolution",
        _t(
            """
            # The French Revolution

            The French Revolution began on 14 July 1789 with the storming of
            the Bastille in Paris. It ended the Bourbon monarchy and ultimately
            led to the rise of Napoleon Bonaparte.

            Causes included financial crisis from France's support of the
            American Revolution, the burden of taxation on the Third Estate,
            and the spread of Enlightenment ideas by Jean-Jacques Rousseau,
            Voltaire, and Montesquieu.

            The Estates-General convened on 5 May 1789 at Versailles. The Third
            Estate declared itself the National Assembly on 17 June. The
            Declaration of the Rights of Man and of the Citizen was adopted on
            26 August 1789.

            King Louis XVI was executed by guillotine on 21 January 1793,
            followed by Marie Antoinette on 16 October 1793. Maximilien
            Robespierre led the Committee of Public Safety during the Reign of
            Terror (September 1793 - July 1794) and was himself guillotined on
            28 July 1794.

            Napoleon Bonaparte seized power in the coup of 18 Brumaire (9
            November 1799), ending the revolutionary period and beginning the
            Napoleonic era.
            """
        ),
    ),
    (
        "industrial_revolution",
        "The Industrial Revolution",
        _t(
            """
            # The Industrial Revolution

            The Industrial Revolution was a period of major industrialisation
            and innovation that began in Great Britain around 1760 and lasted
            to roughly 1840. It transformed economies from agrarian and
            handicraft to industrial and machine-driven.

            James Watt's improved steam engine, developed in partnership with
            Matthew Boulton from 1775 at the Soho Manufactory in Birmingham,
            was a central technology. Watt's separate condenser, patented in
            1769, dramatically improved efficiency over earlier Newcomen
            engines.

            The textile industry was transformed by Richard Arkwright's water
            frame (1769), James Hargreaves's spinning jenny (1764), and Samuel
            Crompton's spinning mule (1779). The first cotton mill using steam
            power was built in Manchester in 1785.

            In iron production, Abraham Darby's use of coke instead of charcoal
            at his Ironbridge Gorge furnace in 1709 enabled mass production.
            Henry Cort's puddling process (1784) further improved wrought iron.

            The Stockton and Darlington Railway, opened in 1825, was the first
            public railway to use steam locomotives. George Stephenson's
            Locomotion No. 1 hauled passengers at up to 15 miles per hour.
            """
        ),
    ),
    (
        "berlin_wall",
        "The Berlin Wall",
        _t(
            """
            # The Berlin Wall

            The Berlin Wall was a guarded concrete barrier that divided West
            Berlin from East Berlin and the surrounding East Germany from 13
            August 1961 to 9 November 1989. Construction was ordered by East
            German leader Walter Ulbricht and implemented by Erich Honecker.

            The wall was built by the German Democratic Republic (GDR) to
            prevent its citizens from fleeing to West Germany via West Berlin.
            Between 1949 and 1961, about 2.5 million East Germans had fled,
            many of them young and educated.

            President John F. Kennedy visited West Berlin on 26 June 1963 and
            delivered his "Ich bin ein Berliner" speech in front of the
            Rathaus Schöneberg. President Ronald Reagan visited on 12 June 1987
            and challenged Soviet leader Mikhail Gorbachev to "tear down this
            wall".

            The wall fell on 9 November 1989 after East German spokesman
            Günter Schabowski mistakenly announced that travel restrictions
            were lifted "immediately" during a press conference. German
            reunification took place on 3 October 1990.
            """
        ),
    ),
    (
        "apollo_moon_landings",
        "The Apollo Moon Landings",
        _t(
            """
            # The Apollo Moon Landings

            The Apollo program was the NASA manned spaceflight project that
            landed humans on the Moon between 1969 and 1972. It was announced
            by President John F. Kennedy in a speech to Congress on 25 May 1961
            and achieved its goal when Apollo 11 landed on 20 July 1969.

            Apollo 11's crew consisted of Neil Armstrong (commander), Buzz
            Aldrin (lunar module pilot), and Michael Collins (command module
            pilot). Armstrong and Aldrin landed the Lunar Module Eagle in the
            Sea of Tranquillity at 20:17 UTC. Armstrong stepped onto the
            surface at 02:56 UTC on 21 July, declaring "that's one small step
            for [a] man, one giant leap for mankind".

            The Saturn V rocket, designed by Wernher von Braun's team at the
            Marshall Space Flight Center in Huntsville, Alabama, launched every
            Apollo mission. The Saturn V stood 110 metres tall and produced 34
            meganewtons of thrust at liftoff.

            Six missions landed on the Moon: Apollo 11, 12, 14, 15, 16, and 17.
            Apollo 13 was a failed landing that became a successful rescue.
            Twelve men walked on the Moon; Eugene Cernan of Apollo 17, in
            December 1972, was the last.
            """
        ),
    ),
    # ---- Philosophy ----
    (
        "enlightenment_thinkers",
        "Key Thinkers of the Enlightenment",
        _t(
            """
            # Key Thinkers of the Enlightenment

            The Enlightenment was an intellectual movement of the 17th and 18th
            centuries that emphasised reason, individualism, and skepticism of
            traditional authority. Its centre was Paris, with salons hosted by
            figures such as Marie Thérèse Rodet Geoffrin.

            Voltaire (François-Marie Arouet, 1694-1778) was a French
            philosopher, writer, and critic of the Catholic Church. He was
            imprisoned in the Bastille in 1717 and exiled to England from 1726
            to 1729. His "Letters Concerning the English Nation" (1733)
            praised British tolerance.

            Jean-Jacques Rousseau (1712-1778), born in Geneva, argued in "The
            Social Contract" (1762) that legitimate authority derives from the
            general will of the people. His views influenced the French
            Revolution.

            Montesquieu (Charles-Louis de Secondat, 1689-1755) proposed the
            separation of powers in "The Spirit of the Laws" (1748). This idea
            shaped the United States Constitution.

            Immanuel Kant (1724-1804), working in Königsberg, published
            "Critique of Pure Reason" in 1781 and his essay "What Is
            Enlightenment?" in 1784, defining it as humanity's emergence from
            self-imposed immaturity.
            """
        ),
    ),
    (
        "stoicism",
        "Stoicism",
        _t(
            """
            # Stoicism

            Stoicism is a school of Hellenistic philosophy founded in Athens by
            Zeno of Citium around 300 BCE. Zeno taught at the Stoa Poikile
            (Painted Porch), from which the school takes its name.

            Stoicism teaches that virtue (arete) is the only good and that
            external things — health, wealth, pleasure — are "preferred
            indifferents". The goal is to live in agreement with nature
            (logos), the rational principle that orders the universe.

            Three Roman Stoics are particularly influential:
            - Epictetus (c. 50-135 CE), a former slave who taught in Nicopolis.
              His "Enchiridion" was compiled by his student Arrian.
            - Seneca (c. 4 BCE - 65 CE), a Roman statesman and tutor to
              Emperor Nero, who ordered him to commit suicide.
            - Marcus Aurelius (121-180 CE), Roman Emperor from 161 to 180. His
              private journal "Meditations" was written in Greek at military
              campaigns on the Danube.

            Modern cognitive behavioural therapy (CBT), developed by Aaron Beck
            and Albert Ellis in the 1960s, draws heavily on Stoic techniques,
            particularly the idea that emotional disturbance comes from
            judgments about events, not the events themselves.
            """
        ),
    ),
    # ---- Geography ----
    (
        "sahara_desert",
        "The Sahara Desert",
        _t(
            """
            # The Sahara Desert

            The Sahara is the largest hot desert in the world, covering about
            9.2 million square kilometres across North Africa. It stretches
            from the Atlantic Ocean in the west to the Red Sea in the east,
            and from the Mediterranean in the north to the Sahel in the south.

            The Sahara spans eleven countries: Algeria, Chad, Egypt, Libya,
            Mali, Mauritania, Morocco, Niger, Sudan, Tunisia, and Western
            Sahara. Major landforms include the Ahaggar Mountains in southern
            Algeria, the Tibesti Mountains in northern Chad, and the Air
            Mountains in northern Niger.

            The highest peak is Emi Koussi, a shield volcano in the Tibesti
            range at 3,445 metres above sea level. The lowest point is the
            Qattara Depression in northwestern Egypt, at 133 metres below sea
            level.

            The Sahara was not always a desert. Between about 10,000 and 5,000
            years ago, during the African Humid Period, the region supported
            lakes, savannah, and human settlements. Rock art at Tassili n'Ajjer
            in Algeria depicts giraffes, hippos, and cattle.

            Major trans-Saharan trade routes connected Timbuktu in Mali to
            Fez in Morocco and Cairo in Egypt, trading gold, salt, and slaves.
            """
        ),
    ),
    (
        "amazon_rainforest",
        "The Amazon Rainforest",
        _t(
            """
            # The Amazon Rainforest

            The Amazon rainforest covers most of the Amazon basin in South
            America, about 5.5 million square kilometres. It spans nine
            countries: Brazil, Peru, Colombia, Venezuela, Ecuador, Bolivia,
            Guyana, Suriname, and French Guiana. About 60% of the forest is in
            Brazil.

            The rainforest is bounded by the Amazon River, which at about
            6,400 km is the longest river in the world by some measures. The
            Amazon originates in the Andes of Peru, near Arequipa, and flows
            eastward to the Atlantic Ocean at Belém, Brazil.

            The Amazon basin is home to about 400 indigenous groups, including
            the Yanomami (Brazil and Venezuela), Kayapó (Brazil), and Asháninka
            (Peru). About 30 million people live in the basin, including the
            cities of Manaus, Belém, and Iquitos.

            The forest contains an estimated 390 billion individual trees
            belonging to about 16,000 species. It produces about 6% of the
            world's oxygen and absorbs about 2 billion tonnes of carbon
            dioxide per year. Deforestation, mainly for cattle ranching and
            soybean farming, has destroyed about 17% of the Brazilian Amazon
            since 1970.
            """
        ),
    ),
    # ---- Companies ----
    (
        "apple_company_history",
        "Apple Inc.: Company History",
        _t(
            """
            # Apple Inc.: Company History

            Apple was founded on 1 April 1976 in Los Altos, California by Steve
            Jobs, Steve Wozniak, and Ronald Wayne. Wayne sold his 10% share
            back to Jobs and Wozniak for USD 800 twelve days later. The
            company's first product, the Apple I, was hand-built by Wozniak in
            Jobs's parents' garage.

            The Apple II, released in 1977, became one of the first
            mass-produced microcomputers. Apple went public on 12 December 1980
            at USD 22 per share, creating more millionaires (about 300) than
            any IPO in history up to that point.

            Steve Jobs was forced out of Apple in 1985 after a power struggle
            with CEO John Sculley. Jobs founded NeXT Computer that year and
            bought the Graphics Group from Lucasfilm in 1986, renaming it
            Pixar. Pixar's "Toy Story", released in 1995, was the first
            feature-length computer-animated film.

            Apple bought NeXT in 1997 for USD 429 million, bringing Jobs back
            as interim CEO. Under Jobs, Apple launched the iMac (1998), iPod
            (2001), iPhone (2007), and iPad (2010). Tim Cook became CEO in
            August 2011; Jobs died on 5 October 2011.

            In August 2018 Apple became the first US company with a USD 1
            trillion market capitalisation. In June 2023 Apple Vision Pro, a
            mixed-reality headset, was announced at WWDC.
            """
        ),
    ),
    (
        "microsoft_history",
        "Microsoft: Company History",
        _t(
            """
            # Microsoft: Company History

            Microsoft was founded in Albuquerque, New Mexico on 4 April 1975
            by Bill Gates and Paul Allen, childhood friends from Seattle. The
            company moved to Bellevue, Washington in 1979 and to Redmond in
            1986.

            Microsoft's breakthrough came in 1980 when IBM chose Microsoft to
            provide an operating system for the IBM PC, launched in August
            1981. Microsoft purchased 86-DOS from Seattle Computer Products
            for USD 50,000, adapted it as MS-DOS, and licensed it to IBM while
            retaining the right to license to other manufacturers. This
            decision enabled the PC compatible industry.

            Windows 1.0 shipped in November 1985. Windows 3.0 (1990) and
            Windows 95 (1995) made Windows the dominant desktop operating
            system. Microsoft Office, launched in 1990, became the dominant
            office suite.

            Bill Gates stepped down as CEO in January 2000, succeeded by Steve
            Ballmer. Satya Nadella became CEO in February 2014 and pivoted
            Microsoft toward cloud computing (Azure) and open source. Microsoft
            acquired LinkedIn in 2016 for USD 26.2 billion, GitHub in 2018 for
            USD 7.5 billion, and Activision Blizzard in 2023 for USD 68.7
            billion.
            """
        ),
    ),
    (
        "amazon_company_history",
        "Amazon: Company History",
        _t(
            """
            # Amazon: Company History

            Amazon was founded by Jeff Bezos in Bellevue, Washington, on 5
            July 1994. Originally named Cadabra (as in abracadabra), Bezos
            renamed it Amazon after the Amazon River and incorporated the
            company on 28 July 1994. The site went live in July 1995.

            Amazon's first product was books. The first book sold was "Fluid
            Concepts and Creative Analogies" by Douglas Hofstadter, shipped in
            April 1995. Amazon went public on 15 May 1997 at USD 18 per share.

            Amazon expanded into music in 1998, into consumer electronics and
            toys in 1999, and into a general marketplace in 2000. Amazon Prime
            launched in February 2005 at USD 79 per year. Amazon Web Services
            (AWS), launched in March 2006, pioneered cloud infrastructure and
            became Amazon's most profitable segment.

            Jeff Bezos stepped down as CEO on 5 July 2021, succeeded by Andy
            Jassy, the former head of AWS. Bezos became Executive Chairman. In
            2013 Bezos purchased The Washington Post for USD 250 million.

            Amazon acquired Whole Foods Market in 2017 for USD 13.4 billion,
            MGM Studios in 2021 for USD 8.5 billion, and iRobot in 2024 (after
            regulatory concessions).
            """
        ),
    ),
    (
        "tesla_company_history",
        "Tesla, Inc.: Company History",
        _t(
            """
            # Tesla, Inc.: Company History

            Tesla was incorporated on 1 July 2003 in Delaware by Martin
            Eberhard and Marc Tarpenning. The company was originally called
            Tesla Motors, named after the Serbian-American inventor Nikola
            Tesla. Elon Musk joined as chairman of the board in February 2004
            after investing USD 6.5 million in the Series A round.

            The Tesla Roadster, launched in 2008, was the first highway-legal
            all-electric vehicle to use lithium-ion battery cells. About 2,450
            Roadsters were sold between 2008 and 2012.

            Eberhard was ousted as CEO in 2007. Musk became CEO in October 2008
            and has held the role since. Tesla's IPO on 29 June 2010 raised USD
            226 million, the first American car company IPO since Ford in 1956.

            The Model S sedan launched in June 2012 and won the 2013 Motor
            Trend Car of the Year. The Model 3, launched in July 2017, became
            the best-selling plug-in electric car in the world. Tesla opened
            its first Gigafactory near Reno, Nevada in 2014. Subsequent
            Gigafactories opened in Shanghai (2019), Berlin (2022), and Austin
            (2022).

            Tesla changed its name from Tesla Motors to Tesla, Inc. in February
            2017 to reflect its expansion into energy storage and solar.
            """
        ),
    ),
    # ---- Literature ----
    (
        "george_orwell",
        "George Orwell",
        _t(
            """
            # George Orwell

            George Orwell was the pen name of Eric Arthur Blair, an English
            novelist, essayist, and critic born in Motihari, Bengal Presidency,
            British India on 25 June 1903. His father Richard Blair worked in
            the Opium Department of the Indian Civil Service.

            Orwell was educated at St Cyprian's School in Eastbourne and at
            Eton College, where he was taught by Aldous Huxley. From 1922 to
            1927 he served in the Indian Imperial Police in Burma, an
            experience that turned him against imperialism and inspired his
            first novel, "Burmese Days" (1934).

            "Animal Farm" was published on 17 August 1945 by Secker and
            Warburg in London. The allegorical novella tells of farm animals
            who revolt against their human farmer, only to be ruled by pigs.
            The character Napoleon is based on Joseph Stalin; Snowball on Leon
            Trotsky; and Old Major on Karl Marx and Vladimir Lenin.

            "Nineteen Eighty-Four" was published on 8 June 1949 by Secker and
            Warburg. It introduced terms like "Big Brother", "doublethink", and
            "thoughtcrime" into the English language. The novel was written at
            Barnhill, a remote farmhouse on the Scottish island of Jura.

            Orwell died of tuberculosis on 21 January 1950 at University
            College Hospital in London, aged 46.
            """
        ),
    ),
    # ---- Medicine ----
    (
        "penicillin_discovery",
        "The Discovery of Penicillin",
        _t(
            """
            # The Discovery of Penicillin

            Penicillin was discovered by Alexander Fleming at St Mary's
            Hospital in London in September 1928. Fleming had left a petri
            dish of Staphylococcus bacteria uncovered, and noticed that a
            mould called Penicillium notatum had killed the bacteria around
            it. He published his findings in the British Journal of
            Experimental Pathology in 1929.

            Fleming could not isolate and produce penicillin in quantity. The
            drug was developed into a practical treatment by Howard Florey,
            Ernst Chain, and their team at the Sir William Dunn School of
            Pathology at the University of Oxford. Their first patient, Albert
            Alexander, was treated in February 1941.

            Mass production during World War II was led by the Northern
            Regional Research Laboratory in Peoria, Illinois. Researchers
            there discovered that a strain of Penicillium chrysogenum found
            on a mouldy cantaloupe in a Peoria market produced much higher
            yields than Fleming's original strain. By D-Day in June 1944,
            American companies were producing enough penicillin to treat all
            severe casualties.

            Fleming, Florey, and Chain shared the 1945 Nobel Prize in
            Physiology or Medicine. Penicillin was the first antibiotic and
            has saved an estimated 200 million lives.
            """
        ),
    ),
    (
        "smallpox_eradication",
        "The Eradication of Smallpox",
        _t(
            """
            # The Eradication of Smallpox

            Smallpox was an infectious disease caused by the Variola virus. It
            killed about 300 million people in the 20th century alone and
            blinded millions more.

            The World Health Organization (WHO) launched an intensified
            eradication campaign in 1967, led by American epidemiologist Donald
            Henderson. The campaign used a strategy of surveillance and
            ring vaccination rather than mass vaccination.

            The last naturally occurring case was Ali Maow Maalin, a hospital
            cook in Merca, Somalia, who became ill on 26 October 1977. He
            survived. The last death from smallpox was Janet Parker, a medical
            photographer at the University of Birmingham Medical School, who
            was infected in August 1978 after the virus escaped from a
            laboratory.

            The WHO declared smallpox eradicated on 8 May 1980. It is the
            only human disease to have been eradicated. Rinderpest, a disease
            of cattle, was declared eradicated in 2011.

            The variola virus is now held officially at only two locations:
            the Centers for Disease Control and Prevention (CDC) in Atlanta,
            Georgia, and the State Research Center of Virology and
            Biotechnology (VECTOR) in Koltsovo, Russia.
            """
        ),
    ),
    # ---- Economics ----
    (
        "keynesian_economics",
        "Keynesian Economics",
        _t(
            """
            # Keynesian Economics

            Keynesian economics is a macroeconomic theory developed by the
            British economist John Maynard Keynes. His landmark book "The
            General Theory of Employment, Interest and Money" was published in
            February 1936 by Macmillan in London, during the Great Depression.

            Keynes argued that aggregate demand — the total spending in an
            economy — is the primary driver of economic activity and employment
            in the short run. He challenged the classical view that markets
            always clear, arguing that inadequate demand could cause prolonged
            unemployment.

            The theory was hugely influential on postwar economic policy,
            particularly in the United States after the Employment Act of 1946.
            Key American Keynesians included Alvin Hansen at Harvard, Paul
            Samuelson at MIT, and Joan Robinson at Cambridge.

            The Keynesian consensus broke down in the 1970s due to
            stagflation — the combination of high inflation and high
            unemployment that simple Keynesian models predicted was impossible.
            Milton Friedman at the University of Chicago led the monetarist
            critique. Robert Lucas and Thomas Sargent developed the rational
            expectations critique, which became New Classical economics.

            Keynesian ideas were revived after the 2008 financial crisis.
            Christina Romer, chair of President Obama's Council of Economic
            Advisers, advocated a fiscal stimulus package that became the
            American Recovery and Reinvestment Act of 2009.
            """
        ),
    ),
    # ---- Climate ----
    (
        "paris_agreement",
        "The Paris Agreement",
        _t(
            """
            # The Paris Agreement

            The Paris Agreement is an international treaty on climate change
            adopted on 12 December 2015 at the 21st Conference of the Parties
            (COP21) to the United Nations Framework Convention on Climate
            Change (UNFCCC). The conference was held at Le Bourget, near
            Paris, France.

            The agreement's long-term goal is to keep the increase in global
            average temperature to well below 2°C above pre-industrial levels,
            and to pursue efforts to limit the increase to 1.5°C. It entered
            into force on 4 November 2016, 30 days after at least 55 parties
            representing at least 55% of global greenhouse gas emissions had
            ratified it.

            As of 2024, 196 parties have ratified the agreement. Each party
            submits a Nationally Determined Contribution (NDC) and is expected
            to update it every five years. The first global stocktake took
            place at COP28 in Dubai in December 2023.

            Key negotiators included Laurent Fabius (French Foreign Minister
            and COP21 president), Christiana Figueres (UNFCCC Executive
            Secretary), and John Kerry (US Secretary of State).

            The United States under President Donald Trump announced
            withdrawal in June 2017, effective 4 November 2020. President Joe
            Biden rejoined the agreement on 20 January 2021, his first day in
            office.
            """
        ),
    ),
    (
        "kyoto_protocol",
        "The Kyoto Protocol",
        _t(
            """
            # The Kyoto Protocol

            The Kyoto Protocol is an international treaty that commits state
            parties to reduce greenhouse gas emissions, based on the scientific
            consensus that global warming is occurring and that human-made
            CO2 emissions are driving it. It was adopted on 11 December 1997
            in Kyoto, Japan, and entered into force on 16 February 2005.

            The Protocol implemented the UNFCCC's objective to stabilise
            greenhouse gas concentrations. It placed different obligations on
            developed (Annex I) and developing countries, following the
            principle of "common but differentiated responsibilities". The
            target for Annex I parties was an average 5% reduction from 1990
            levels over the 2008-2012 commitment period.

            The United States signed the Protocol on 12 November 1998 under
            President Bill Clinton, but the Senate had already passed the
            Byrd-Hagel Resolution 95-0 in July 1997 opposing any treaty that
            did not include developing country commitments. President George
            W. Bush withdrew the US signature in March 2001.

            Canada withdrew from the Protocol in December 2011, effective
            December 2012, to avoid about CAD 14 billion in penalties.

            The Doha Amendment (2012) established a second commitment period
            (2013-2020). The Paris Agreement (2015) effectively replaced
            Kyoto from 2020 onward.
            """
        ),
    ),
    # ---- Math ----
    (
        "fermat_last_theorem",
        "Fermat's Last Theorem",
        _t(
            """
            # Fermat's Last Theorem

            Fermat's Last Theorem states that no three positive integers a, b,
            c satisfy the equation a^n + b^n = c^n for any integer n > 2. It
            was first conjectured by Pierre de Fermat in 1637, in the margin
            of his copy of Diophantus's "Arithmetica".

            Fermat wrote: "I have discovered a truly marvellous proof of this,
            which this margin is too narrow to contain." Mathematicians spent
            358 years trying to find this proof.

            Important partial results came from Sophie Germain in the early
            19th century, who proved the theorem for a class of primes now
            called Germain primes. Ernst Kummer in 1847 proved it for all
            regular primes.

            Andrew Wiles, working at Princeton University, proved the
            semistable case of the Taniyama-Shimura-Weil conjecture (now the
            modularity theorem). Combined with work by Ken Ribet at UC
            Berkeley showing that this conjecture implied Fermat's Last
            Theorem, this gave the proof. Wiles announced his proof on 23 June
            1993 in a series of lectures at the Isaac Newton Institute in
            Cambridge, England.

            A gap was found in the original proof. Wiles and his former
            student Richard Taylor fixed it, and the final paper was published
            in Annals of Mathematics in 1995. Wiles was knighted in 2000 and
            received the 2016 Abel Prize.
            """
        ),
    ),
    (
        "riemann_hypothesis",
        "The Riemann Hypothesis",
        _t(
            """
            # The Riemann Hypothesis

            The Riemann Hypothesis is a conjecture about the zeros of the
            Riemann zeta function, formulated by the German mathematician
            Bernhard Riemann in 1859. The zeta function is defined for
            complex numbers s with real part greater than 1 by the series
            zeta(s) = sum from n=1 to infinity of 1/n^s.

            The hypothesis states that all non-trivial zeros of the zeta
            function lie on the "critical line" Re(s) = 1/2. It is one of the
            seven Millennium Prize Problems established by the Clay
            Mathematics Institute in 2000, with a USD 1 million prize for a
            proof or disproof.

            The hypothesis is deeply connected to the distribution of prime
            numbers. An equivalent formulation, due to von Mangoldt, is that
            the prime counting function pi(x) is approximated by the
            logarithmic integral Li(x) with error bounded by sqrt(x) log(x).

            Riemann, working at the University of Göttingen, computed the
            first few non-trivial zeros himself. As of 2024, the first 10
            trillion zeros have been verified to lie on the critical line,
            beginning with computations by Alan Turing in 1953. Turing also
            designed a mechanical calculator for this purpose at the
            University of Manchester.

            Other mathematicians who contributed include G.H. Hardy, who in
            1914 proved that infinitely many zeros lie on the critical line,
            and Hugh Montgomery, whose 1972 pair correlation conjecture
            revealed unexpected connections to random matrix theory.
            """
        ),
    ),
    # ---- Add more to reach 50 ----
    (
        "berlin_conference_1884",
        "The Berlin Conference of 1884",
        _t(
            """
            # The Berlin Conference of 1884

            The Berlin Conference (German: Kongokonferenz), held from 15
            November 1884 to 26 February 1885 in Berlin, Germany, regulated
            European colonisation and trade in Africa during the New
            Imperialism period. It was organised by Otto von Bismarck, the
            Chancellor of Germany.

            The conference was attended by representatives of 14 nations:
            Austria-Hungary, Belgium, Denmark, France, Germany, Great Britain,
            Italy, the Netherlands, the Ottoman Empire, Portugal, Russia,
            Spain, Sweden-Norway, and the United States. Notably, no African
            representatives were present.

            The conference recognised King Leopold II of Belgium's claim to
            the Congo Free State, a personal possession roughly 76 times the
            size of Belgium. Leopold's brutal regime, exposed by Roger
            Casement and E.D. Morel in the Casement Report of 1904, killed an
            estimated 10 million Congolese.

            The General Act of the Berlin Conference defined the rules for
            future claims: a European power could claim territory only by
            physical occupation, notify other signatories, and establish
            authority. The principle of "effective occupation" accelerated the
            Scramble for Africa.

            Within 25 years of the conference, almost the entire African
            continent had been partitioned. Only Ethiopia, under Emperor
            Menelik II, and Liberia remained independent.
            """
        ),
    ),
    (
        "manhattan_project",
        "The Manhattan Project",
        _t(
            """
            # The Manhattan Project

            The Manhattan Project was the US research and development program
            that produced the first nuclear weapons during World War II. It
            was led by the United States with support from the United Kingdom
            and Canada.

            The project grew out of the Einstein-Szilárd letter of 2 August
            1939, in which physicists Albert Einstein and Leó Szilárd warned
            President Franklin D. Roosevelt that Nazi Germany might develop
            nuclear weapons. The letter was delivered by Alexander Sachs.

            Major General Leslie Groves of the US Army Corps of Engineers was
            appointed director in September 1942. He appointed physicist J.
            Robert Oppenheimer to lead the secret weapons laboratory at Los
            Alamos, New Mexico.

            The first nuclear device, codenamed "the Gadget", was detonated
            in the Trinity test on 16 July 1945 at the Alamogordo Bombing
            Range in New Mexico. The "Fat Man" plutonium bomb was dropped on
            Nagasaki on 9 August 1945; the "Little Boy" uranium bomb was
            dropped on Hiroshima on 6 August 1945.

            Major sites included the Hanford Site in Washington state
            (plutonium production, led by Glenn Seaborg), the Clinton Engineer
            Works at Oak Ridge, Tennessee (uranium enrichment), and the
            Metallurgical Laboratory at the University of Chicago (led by
            Enrico Fermi, who built the first nuclear reactor, Chicago Pile-1,
            on 2 December 1942).
            """
        ),
    ),
    (
        "printing_press",
        "Gutenberg and the Printing Press",
        _t(
            """
            # Gutenberg and the Printing Press

            Johannes Gutenberg (c. 1400 - 1468) was a German inventor who
            introduced movable type printing to Europe. He was born in Mainz,
            Germany, the son of a patrician named Friele Gensfleisch zur
            Laden.

            Gutenberg's key innovations, developed in Strasbourg in the 1440s
            and later in Mainz, were: a hand mould for casting movable metal
            type, an oil-based ink that adhered to metal type, and a
            modification of the agricultural screw press to apply even
            pressure across a page.

            The Gutenberg Bible, also called the 42-line Bible, was printed in
            Mainz between 1450 and 1455. About 180 copies were originally
            produced, of which 49 survive. The British Library in London
            holds two complete paper copies and one vellum copy.

            Gutenberg's financier Johann Fust sued him in 1455 for repayment
            of loans totalling about 1,600 guilders. The court awarded
            Gutenberg's workshop and equipment to Fust, who continued the
            printing business with Gutenberg's former employee Peter Schöffer.

            The printing press catalysed the Reformation (Martin Luther's 95
            Theses of 1517 were printed and distributed across Europe in
            weeks), the Scientific Revolution, and the Enlightenment. It is
            widely considered one of the most influential inventions in
            history.
            """
        ),
    ),
    (
        "magna_carta",
        "Magna Carta",
        _t(
            """
            # Magna Carta

            Magna Carta Libertatum (Medieval Latin for "Great Charter of
            Freedoms") is a royal charter of rights agreed to by King John of
            England at Runnymede, near Windsor, on 15 June 1215. It was
            sealed, not signed, by the King.

            The charter was brokered by Archbishop of Canterbury Stephen
            Langton in response to a rebellion by barons angry at King John's
            heavy taxation, military failures in France (especially the loss
            of Normandy in 1204), and disputes with Pope Innocent III.

            Clause 39 — "No free man shall be seized or imprisoned... except
            by the lawful judgment of his equals or by the law of the land" —
            became the foundation of habeas corpus and the right to due
            process. Clause 40 — "To no one will we sell, to no one will we
            refuse or delay right or justice" — is the foundation of access to
            justice.

            King John almost immediately persuaded Pope Innocent III to annul
            the charter, leading to the First Barons' War. After John's death
            in October 1216, his son Henry III reissued a shortened version in
            1216, 1217, and 1225.

            The 1297 Inspeximus issue of Magna Carta by Edward I entered the
            English statute roll, where most of it remained legally valid
            until the 19th and 20th centuries. Four copies of the 1215 charter
            survive: two at the British Library, one at Salisbury Cathedral,
            and one at Lincoln Castle.
            """
        ),
    ),
    (
        "euro_currency",
        "The Euro",
        _t(
            """
            # The Euro

            The euro (symbol: EUR, code: EUR) is the official currency of 20
            of the 27 member states of the European Union. These countries
            form the eurozone: Austria, Belgium, Croatia, Cyprus, Estonia,
            Finland, France, Germany, Greece, Ireland, Italy, Latvia,
            Lithuania, Luxembourg, Malta, the Netherlands, Portugal, Slovakia,
            Slovenia, and Spain.

            The euro was introduced to world financial markets as an
            accounting currency on 1 January 1999, replacing the former
            European Currency Unit (ECU) at a 1:1 ratio. Euro notes and coins
            entered circulation on 1 January 2002.

            The currency is administered by the European Central Bank (ECB),
            based in Frankfurt, Germany, and the Eurosystem of national
            central banks. The ECB's first president was Wim Duisenberg of
            the Netherlands (1998-2003), followed by Jean-Claude Trichet of
            France (2003-2011), Mario Draghi of Italy (2011-2019), and
            Christine Lagarde of France (2019-present).

            The Maastricht Treaty of 1992 established the legal framework for
            the euro. To join, countries must meet convergence criteria
            including a budget deficit below 3% of GDP and public debt below
            60% of GDP.

            Croatia was the most recent country to adopt the euro, on 1
            January 2023. Denmark has an opt-out from joining, and Sweden has
            intentionally failed to meet the convergence criteria.
            """
        ),
    ),
    (
        "bitcoin_whitepaper",
        "Bitcoin",
        _t(
            """
            # Bitcoin

            Bitcoin is a decentralised digital currency, invented by an
            unknown person or group using the pseudonym Satoshi Nakamoto. The
            white paper "Bitcoin: A Peer-to-Peer Electronic Cash System" was
            published on 31 October 2008 to a cryptography mailing list.

            The Bitcoin network went live on 3 January 2009, when the
            genesis block was mined by Nakamoto. The genesis block contains
            the text "The Times 03/Jan/2009 Chancellor on brink of second
            bailout for banks", referring to a headline in that day's edition
            of The Times of London.

            The first Bitcoin transaction took place on 12 January 2009, when
            Nakamoto sent 10 BTC to Hal Finney, a developer who had downloaded
            the software on the day of its release. The first commercial
            transaction was on 22 May 2010, when programmer Laszlo Hanyecz
            bought two pizzas from Papa John's for 10,000 BTC.

            Nakamoto stepped back from the project in 2010, handing
            development to Gavin Andresen. The identity of Nakamoto remains
            unknown, despite investigations of candidates including Nick
            Szabo, Dorian Nakamoto, Craig Wright (whose claims were rejected
            by a UK court in March 2024), and Hal Finney.

            Bitcoin uses the SHA-256 hash function designed by the NSA.
            Mining rewards were halved (the "halving") in 2012, 2016, 2020,
            and 2024, reducing from 50 BTC per block to 3.125 BTC per block
            as of April 2024. The supply is capped at 21 million BTC.
            """
        ),
    ),
    (
        "web_brief_history",
        "A Brief History of the Web",
        _t(
            """
            # A Brief History of the Web

            The World Wide Web was invented by Tim Berners-Lee at CERN, the
            European Organization for Nuclear Research near Geneva, in 1989.
            He submitted a proposal on 12 March 1989 to his supervisor Mike
            Sendall, who scrawled "Vague but exciting..." on the cover.

            The first website went live on 20 December 1990 at
            info.cern.ch. It described what the Web was and how to use it. The
            first web browser, also written by Berners-Lee, ran on a NeXT
            computer.

            The first widely popular browser was Mosaic, released in April
            1993 by the National Center for Supercomputing Applications
            (NCSA) at the University of Illinois. Marc Andreessen and Eric
            Bina led the team. Andreessen then co-founded Netscape with Jim
            Clark in April 1994.

            Microsoft released Internet Explorer 1.0 in August 1995 as part
            of the Windows 95 Plus! pack. The resulting "browser wars" of the
            late 1990s ended with Netscape's near-disappearance, but Netscape
            released its source code in March 1998, creating the Mozilla
            Project that would eventually produce Firefox.

            Web 2.0, a term popularised by Tim O'Reilly in 2004, describes
            the shift from static pages to user-generated content. Web 3.0
            refers to a decentralised web based on blockchain technology,
            although the term is contested.
            """
        ),
    ),
    (
        "eiffel_tower",
        "The Eiffel Tower",
        _t(
            """
            # The Eiffel Tower

            The Eiffel Tower is a wrought-iron lattice tower on the Champ de
            Mars in Paris, France. It is named after the engineer Gustave
            Eiffel, whose company Compagnie des Établissements Eiffel designed
            and built the tower between 1887 and 1889.

            The tower was the entrance arch for the 1889 Exposition
            Universelle (World's Fair), held to celebrate the 100th
            anniversary of the French Revolution. It was originally 312 metres
            tall; with later additions of antennas it now stands 330 metres.

            The chief engineers were Maurice Koechlin and Émile Nouguier,
            who conceived the design in 1884. The architect Stephen Sauvestre
            added decorative arches and a glass pavilion. Eiffel initially
            rejected the design but later championed it.

            The tower was originally intended to stand for 20 years and be
            dismantled in 1909. It was saved because its height made it
            valuable for radio telegraphy. The French military used it to
            intercept German radio messages during World War I, and it became
            part of the French broadcasting network.

            The tower is painted every seven years, requiring about 60 tonnes
            of paint. It is the most-visited paid monument in the world: about
            7 million people ascend it each year. The towers has 1,665 steps
            to the top, though visitors can only climb to the second floor
            (674 steps).
            """
        ),
    ),
    (
        "voyager_mission",
        "The Voyager Program",
        _t(
            """
            # The Voyager Program

            The Voyager program is a NASA scientific program that launched two
            unmanned space probes, Voyager 1 and Voyager 2, in 1977. They were
            originally designed to study Jupiter and Saturn, but their
            missions were extended.

            Voyager 2 launched first, on 20 August 1977, aboard a Titan IIIE
            rocket from Cape Canaveral, Florida. Voyager 1 launched on 5
            September 1977. Both spacecraft were built at the Jet Propulsion
            Laboratory (JPL) in Pasadena, California, which continues to
            operate them.

            Voyager 1 flew past Jupiter in March 1979 and Saturn in November
            1980, then continued northward out of the ecliptic plane. Voyager
            2 flew past Jupiter in July 1979, Saturn in August 1981, and
            became the first and only spacecraft to visit Uranus (January
            1986) and Neptune (August 1989).

            Voyager 1 crossed the heliopause — the boundary where the Sun's
            solar wind gives way to interstellar medium — on 25 August 2012,
            becoming the first human-made object to enter interstellar space.
            Voyager 2 crossed on 5 November 2018.

            Each Voyager carries a Golden Record, a 12-inch gold-plated
            copper phonograph record containing sounds and images of Earth,
            selected by a committee led by Carl Sagan. The records include
            greetings in 55 languages, music by Bach, Beethoven, and Chuck
            Berry, and a recorded message from President Jimmy Carter.
            """
        ),
    ),
    (
        "harvey_hurricane",
        "Hurricane Harvey",
        _t(
            """
            # Hurricane Harvey

            Hurricane Harvey was a devastating Category 4 Atlantic hurricane
            that made landfall in Texas and Louisiana in August 2017. It was
            the costliest tropical cyclone on record at the time, tied with
            Hurricane Katrina in 2005, causing about USD 125 billion in
            damage.

            Harvey originated from a tropical wave east of the Lesser Antilles
            on 17 August 2017. It crossed the Windward Islands on 18 August,
            degenerated into a tropical wave over the Caribbean Sea, then
            regenerated in the Bay of Campeche on 23 August.

            The storm intensified rapidly on 24 August, becoming a Category 4
            hurricane with winds of 130 mph (215 km/h) before making landfall
            near Rockport, Texas on 26 August 2017. It then stalled over
            southeastern Texas for four days, dropping unprecedented rainfall.

            Houston, the fourth-largest US city, received more than 40 inches
            (1,000 mm) of rain in some areas, with a maximum of 60.58 inches
            (1,539 mm) recorded near Nederland, Texas. This exceeded the
            previous US rainfall record for a single tropical cyclone.

            The Federal Emergency Management Agency (FEMA) reported more than
            30,000 people were rescued from floodwaters, and about 40,000 were
            displaced to shelters. At least 68 people died directly from the
            storm in Texas. The National Hurricane Center's retrospective
            report attributed 103 deaths to Harvey.
            """
        ),
    ),
    (
        "space_x_falcon",
        "SpaceX and the Falcon 9",
        _t(
            """
            # SpaceX and the Falcon 9

            SpaceX (Space Exploration Technologies Corp.) was founded on 14
            March 2002 by Elon Musk, who had just sold PayPal to eBay for USD
            1.5 billion. The company's first office was in El Segundo,
            California, before moving to Hawthorne in 2008.

            The Falcon 1 was SpaceX's first orbital launch vehicle. After
            three failed launches in 2006, 2007, and 2008, Falcon 1
            successfully placed the RazakSAT satellite in orbit on 14
            September 2008, becoming the first privately developed
            liquid-fueled rocket to reach orbit.

            The Falcon 9, named for its nine Merlin engines, first launched on
            4 June 2010 from Cape Canaveral. The Falcon 9 v1.1 first flew in
            September 2013, and the current "Full Thrust" version in December
            2015. On 21 December 2015, Falcon 9 performed the first successful
            vertical landing of an orbital-class rocket stage, at Landing Zone
            1 at Cape Canaveral.

            The Dragon spacecraft became the first commercial spacecraft to
            dock with the International Space Station on 25 May 2012. The
            Crew Dragon carried NASA astronauts Bob Behnken and Doug Hurley to
            the ISS on 30 May 2020 in the Demo-2 mission, the first crewed
            orbital launch from US soil since the Space Shuttle's retirement
            in 2011.

            The Starship program, conducted at the SpaceX Starbase facility
            near Boca Chica, Texas, achieved its first successful orbital
            flight and splashdown on 14 March 2024. The Super Heavy booster
            was caught by the launch tower's "chopstick" arms on 13 October
            2024.
            """
        ),
    ),
]


assert len(ARTICLES) >= 50, f"Expected at least 50 articles, got {len(ARTICLES)}"


# --------------------------------------------------------------------------
# Distribution: 20 md, 15 html, 15 pdf
# --------------------------------------------------------------------------

def _assign_kinds() -> list[str]:
    n = len(ARTICLES)
    n_pdf = n // 4          # ~25%
    n_html = n // 4         # ~25%
    n_md = n - n_pdf - n_html  # ~50%
    kinds = ["md"] * n_md + ["html"] * n_html + ["pdf"] * n_pdf
    random.shuffle(kinds)
    return kinds


def _write_markdown(path: Path, title: str, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def _write_html(path: Path, title: str, body: str) -> None:
    # Strip the leading H1 from body since we render our own <h1>.
    body_no_h1 = "\n".join(l for l in body.splitlines() if not l.startswith("# "))
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>body{{font-family:Georgia,serif;max-width:42em;margin:2em auto;line-height:1.5}}h1{{color:#222}}</style>
</head>
<body>
  <h1>{title}</h1>
  <article>
{_html_paragraphs(body_no_h1)}
  </article>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def _html_paragraphs(body: str) -> str:
    paras = [p.strip() for p in body.strip().split("\n\n") if p.strip()]
    return "\n".join(f"    <p>{p}</p>" for p in paras)


def _write_pdf(path: Path, title: str, body: str) -> None:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    from reportlab.lib.enums import TA_LEFT

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=18, leading=22, spaceAfter=14, alignment=TA_LEFT)
    p = ParagraphStyle("p", parent=styles["BodyText"], fontSize=11, leading=15, spaceAfter=8, alignment=TA_LEFT)
    doc = SimpleDocTemplate(
        str(path),
        pagesize=LETTER,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
        title=title,
        author="Knowledge Manager sample dataset",
    )
    flowables = [Paragraph(title, h1), Spacer(1, 0.2 * inch)]
    for para in [pp.strip() for pp in body.split("\n\n") if pp.strip()]:
        # Drop a leading "# " H1 since we already have a Title
        if para.startswith("# "):
            continue
        # Escape ampersands for reportlab
        safe = para.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        flowables.append(Paragraph(safe, p))
    doc.build(flowables)


# --------------------------------------------------------------------------
# Labels + Q&A
# --------------------------------------------------------------------------

# Hand-curated entity + relationship labels for 20 of the 50 docs.
LABELS: dict[str, dict] = {
    "alan_turing_life": {
        "entities": [
            ("Alan Turing", "person"),
            ("London", "place"),
            ("University of Cambridge", "org"),
            ("Bletchley Park", "place"),
            ("Bombe", "concept"),
            ("Enigma", "concept"),
            ("National Physical Laboratory", "org"),
            ("Automatic Computing Engine", "concept"),
            ("University of Manchester", "org"),
            ("Manchester Mark 1", "concept"),
            ("Gordon Brown", "person"),
        ],
        "relationships": [
            ("Alan Turing", "born_in", "London"),
            ("Alan Turing", "studied_at", "University of Cambridge"),
            ("Alan Turing", "worked_at", "Bletchley Park"),
            ("Alan Turing", "designed", "Bombe"),
            ("Bombe", "cracked", "Enigma"),
            ("Alan Turing", "worked_at", "National Physical Laboratory"),
            ("Alan Turing", "designed", "Automatic Computing Engine"),
            ("Alan Turing", "worked_at", "University of Manchester"),
            ("Alan Turing", "worked_on", "Manchester Mark 1"),
            ("Gordon Brown", "apologised_for", "Alan Turing"),
        ],
    },
    "bletchley_park": {
        "entities": [
            ("Bletchley Park", "place"),
            ("Milton Keynes", "place"),
            ("Government Code and Cypher School", "org"),
            ("GCHQ", "org"),
            ("Alan Turing", "person"),
            ("Gordon Welchman", "person"),
            ("Hugh Alexander", "person"),
            ("Joan Clarke", "person"),
            ("Enigma", "concept"),
            ("Lorenz", "concept"),
            ("Bombe", "concept"),
            ("Harold Keen", "person"),
            ("British Tabulating Machine Company", "org"),
            ("Letchworth", "place"),
            ("National Museum of Computing", "org"),
            ("Colossus", "concept"),
            ("Tommy Flowers", "person"),
        ],
        "relationships": [
            ("Bletchley Park", "located_in", "Milton Keynes"),
            ("Government Code and Cypher School", "predecessor_of", "GCHQ"),
            ("Alan Turing", "worked_at", "Bletchley Park"),
            ("Gordon Welchman", "worked_at", "Bletchley Park"),
            ("Hugh Alexander", "worked_at", "Bletchley Park"),
            ("Joan Clarke", "worked_at", "Bletchley Park"),
            ("Bletchley Park", "cracked", "Enigma"),
            ("Bletchley Park", "cracked", "Lorenz"),
            ("Alan Turing", "designed", "Bombe"),
            ("Harold Keen", "manufactured", "Bombe"),
            ("British Tabulating Machine Company", "located_in", "Letchworth"),
            ("Tommy Flowers", "designed", "Colossus"),
            ("National Museum of Computing", "located_in", "Bletchley Park"),
        ],
    },
    "enigma_machine": {
        "entities": [
            ("Enigma", "concept"),
            ("Arthur Scherbius", "person"),
            ("Kriegsmarine", "org"),
            ("M4", "concept"),
            ("Cipher Bureau", "org"),
            ("Marian Rejewski", "person"),
            ("Bletchley Park", "place"),
            ("Alan Turing", "person"),
            ("Bombe", "concept"),
        ],
        "relationships": [
            ("Arthur Scherbius", "invented", "Enigma"),
            ("Kriegsmarine", "used", "M4"),
            ("M4", "variant_of", "Enigma"),
            ("Marian Rejewski", "worked_at", "Cipher Bureau"),
            ("Cipher Bureau", "broke", "Enigma"),
            ("Alan Turing", "worked_at", "Bletchley Park"),
            ("Bletchley Park", "broke", "Enigma"),
            ("Alan Turing", "designed", "Bombe"),
        ],
    },
    "turing_machine_concept": {
        "entities": [
            ("Turing machine", "concept"),
            ("Alan Turing", "person"),
            ("Church-Turing thesis", "concept"),
            ("Alonzo Church", "person"),
            ("Halting Problem", "concept"),
            ("universal Turing machine", "concept"),
        ],
        "relationships": [
            ("Alan Turing", "invented", "Turing machine"),
            ("Church-Turing thesis", "formulated_by", "Alonzo Church"),
            ("Church-Turing thesis", "formulated_by", "Alan Turing"),
            ("Alan Turing", "proved_undecidable", "Halting Problem"),
            ("universal Turing machine", "invented_by", "Alan Turing"),
        ],
    },
    "ai_winter_1970s": {
        "entities": [
            ("first AI winter", "concept"),
            ("Georgetown-IBM experiment", "concept"),
            ("ALPAC", "org"),
            ("National Research Council", "org"),
            ("Frank Rosenblatt", "person"),
            ("Perceptron", "concept"),
            ("Marvin Minsky", "person"),
            ("Seymour Papert", "person"),
            ("Lighthill Report", "concept"),
            ("Science Research Council", "org"),
            ("XCON", "concept"),
            ("Digital Equipment Corporation", "org"),
            ("Fifth Generation Computer Systems", "concept"),
            ("MITI", "org"),
        ],
        "relationships": [
            ("ALPAC", "commissioned_by", "National Research Council"),
            ("Frank Rosenblatt", "invented", "Perceptron"),
            ("Marvin Minsky", "co_authored_with", "Seymour Papert"),
            ("Lighthill Report", "commissioned_by", "Science Research Council"),
            ("XCON", "developed_by", "Digital Equipment Corporation"),
            ("Fifth Generation Computer Systems", "launched_by", "MITI"),
        ],
    },
    "deep_learning_rise": {
        "entities": [
            ("Geoff Hinton", "person"),
            ("David Rumelhart", "person"),
            ("backpropagation", "concept"),
            ("Yann LeCun", "person"),
            ("convolutional neural networks", "concept"),
            ("Bell Labs", "org"),
            ("Alex Krizhevsky", "person"),
            ("Ilya Sutskever", "person"),
            ("AlexNet", "concept"),
            ("ImageNet", "concept"),
            ("NVIDIA", "org"),
            ("Sepp Hochreiter", "person"),
            ("Jürgen Schmidhuber", "person"),
            ("LSTM", "concept"),
            ("Ashish Vaswani", "person"),
            ("Google", "org"),
            ("Transformer", "concept"),
            ("OpenAI", "org"),
            ("GPT", "concept"),
            ("BERT", "concept"),
        ],
        "relationships": [
            ("Geoff Hinton", "co_authored", "backpropagation"),
            ("David Rumelhart", "co_authored", "backpropagation"),
            ("Yann LeCun", "invented", "convolutional neural networks"),
            ("Yann LeCun", "worked_at", "Bell Labs"),
            ("Alex Krizhevsky", "developed", "AlexNet"),
            ("Ilya Sutskever", "developed", "AlexNet"),
            ("Geoff Hinton", "developed", "AlexNet"),
            ("AlexNet", "won", "ImageNet"),
            ("Sepp Hochreiter", "invented", "LSTM"),
            ("Jürgen Schmidhuber", "invented", "LSTM"),
            ("Ashish Vaswani", "introduced", "Transformer"),
            ("Transformer", "developed_at", "Google"),
            ("OpenAI", "released", "GPT"),
            ("Google", "released", "BERT"),
        ],
    },
    "transformer_architecture": {
        "entities": [
            ("Transformer", "concept"),
            ("Ashish Vaswani", "person"),
            ("Google", "org"),
            ("multi-head self-attention", "concept"),
            ("encoder", "concept"),
            ("decoder", "concept"),
            ("BERT", "concept"),
            ("Devlin", "person"),
            ("GPT", "concept"),
            ("Radford", "person"),
            ("T5", "concept"),
            ("Raffel", "person"),
        ],
        "relationships": [
            ("Transformer", "introduced_by", "Ashish Vaswani"),
            ("Transformer", "developed_at", "Google"),
            ("Transformer", "uses", "multi-head self-attention"),
            ("BERT", "developed_by", "Devlin"),
            ("GPT", "developed_by", "Radford"),
            ("T5", "developed_by", "Raffel"),
        ],
    },
    "openai_company": {
        "entities": [
            ("OpenAI", "org"),
            ("Sam Altman", "person"),
            ("Elon Musk", "person"),
            ("Ilya Sutskever", "person"),
            ("Greg Brockman", "person"),
            ("Wojciech Zaremba", "person"),
            ("John Schulman", "person"),
            ("San Francisco", "place"),
            ("Microsoft", "org"),
            ("GPT-2", "concept"),
            ("GPT-3", "concept"),
            ("GPT-4", "concept"),
            ("GPT-4o", "concept"),
            ("DALL-E", "concept"),
            ("Whisper", "concept"),
            ("Sora", "concept"),
            ("ChatGPT", "concept"),
        ],
        "relationships": [
            ("OpenAI", "founded_by", "Sam Altman"),
            ("OpenAI", "founded_by", "Elon Musk"),
            ("OpenAI", "founded_by", "Ilya Sutskever"),
            ("OpenAI", "founded_by", "Greg Brockman"),
            ("OpenAI", "founded_by", "Wojciech Zaremba"),
            ("OpenAI", "founded_by", "John Schulman"),
            ("OpenAI", "located_in", "San Francisco"),
            ("Microsoft", "invested_in", "OpenAI"),
            ("OpenAI", "released", "GPT-2"),
            ("OpenAI", "released", "GPT-3"),
            ("OpenAI", "released", "GPT-4"),
            ("OpenAI", "released", "GPT-4o"),
            ("OpenAI", "released", "DALL-E"),
            ("OpenAI", "released", "Whisper"),
            ("OpenAI", "released", "Sora"),
            ("OpenAI", "released", "ChatGPT"),
        ],
    },
    "anthropic_company": {
        "entities": [
            ("Anthropic", "org"),
            ("Dario Amodei", "person"),
            ("Daniela Amodei", "person"),
            ("San Francisco", "place"),
            ("Google", "org"),
            ("Spark Capital", "org"),
            ("Amazon", "org"),
            ("Claude", "concept"),
            ("Claude 2", "concept"),
            ("Claude 3", "concept"),
            ("Haiku", "concept"),
            ("Sonnet", "concept"),
            ("Opus", "concept"),
            ("Claude 3.5 Sonnet", "concept"),
            ("Constitutional AI", "concept"),
            ("Model Context Protocol", "concept"),
        ],
        "relationships": [
            ("Anthropic", "founded_by", "Dario Amodei"),
            ("Anthropic", "founded_by", "Daniela Amodei"),
            ("Anthropic", "located_in", "San Francisco"),
            ("Google", "invested_in", "Anthropic"),
            ("Spark Capital", "invested_in", "Anthropic"),
            ("Amazon", "invested_in", "Anthropic"),
            ("Anthropic", "released", "Claude"),
            ("Anthropic", "released", "Claude 2"),
            ("Anthropic", "released", "Claude 3"),
            ("Claude 3", "variant", "Haiku"),
            ("Claude 3", "variant", "Sonnet"),
            ("Claude 3", "variant", "Opus"),
            ("Anthropic", "released", "Claude 3.5 Sonnet"),
            ("Anthropic", "developed", "Constitutional AI"),
            ("Anthropic", "developed", "Model Context Protocol"),
        ],
    },
    "google_deepmind": {
        "entities": [
            ("DeepMind", "org"),
            ("Demis Hassabis", "person"),
            ("Shane Legg", "person"),
            ("Mustafa Suleyman", "person"),
            ("London", "place"),
            ("Google", "org"),
            ("AlphaGo", "concept"),
            ("Lee Sedol", "person"),
            ("Seoul", "place"),
            ("AlphaZero", "concept"),
            ("AlphaFold", "concept"),
            ("John Jumper", "person"),
            ("Google DeepMind", "org"),
            ("Gemini", "concept"),
            ("David Silver", "person"),
            ("Volodymyr Mnih", "person"),
            ("Oriol Vinyals", "person"),
        ],
        "relationships": [
            ("DeepMind", "founded_by", "Demis Hassabis"),
            ("DeepMind", "founded_by", "Shane Legg"),
            ("DeepMind", "founded_by", "Mustafa Suleyman"),
            ("DeepMind", "located_in", "London"),
            ("Google", "acquired", "DeepMind"),
            ("AlphaGo", "defeated", "Lee Sedol"),
            ("AlphaGo", "played_in", "Seoul"),
            ("DeepMind", "developed", "AlphaZero"),
            ("DeepMind", "developed", "AlphaFold"),
            ("AlphaFold", "developed_by", "John Jumper"),
            ("Google", "merged_with", "DeepMind"),
            ("Google DeepMind", "developed", "Gemini"),
            ("David Silver", "led", "AlphaGo"),
            ("Volodymyr Mnih", "authored", "DQN"),
        ],
    },
    "crispr_gene_editing": {
        "entities": [
            ("CRISPR", "concept"),
            ("CRISPR-Cas9", "concept"),
            ("Jennifer Doudna", "person"),
            ("University of California Berkeley", "org"),
            ("Emmanuelle Charpentier", "person"),
            ("Max Planck Institute", "org"),
            ("Berlin", "place"),
            ("Cas9", "concept"),
            ("Feng Zhang", "person"),
            ("Broad Institute", "org"),
            ("George Church", "person"),
            ("Harvard", "org"),
            ("Casgevy", "concept"),
            ("Medicines and Healthcare products Regulatory Agency", "org"),
        ],
        "relationships": [
            ("Jennifer Doudna", "developed", "CRISPR-Cas9"),
            ("Emmanuelle Charpentier", "developed", "CRISPR-Cas9"),
            ("Jennifer Doudna", "worked_at", "University of California Berkeley"),
            ("Emmanuelle Charpentier", "worked_at", "Max Planck Institute"),
            ("Max Planck Institute", "located_in", "Berlin"),
            ("Feng Zhang", "worked_at", "Broad Institute"),
            ("George Church", "worked_at", "Harvard"),
            ("Feng Zhang", "demonstrated", "CRISPR-Cas9"),
            ("George Church", "demonstrated", "CRISPR-Cas9"),
            ("Medicines and Healthcare products Regulatory Agency", "approved", "Casgevy"),
        ],
    },
    "roman_republic": {
        "entities": [
            ("Roman Republic", "concept"),
            ("Roman Kingdom", "concept"),
            ("Augustus", "person"),
            ("Senate", "org"),
            ("Lucius Junius Brutus", "person"),
            ("Tarquin the Proud", "person"),
            ("Cincinnatus", "person"),
            ("Tiberius Gracchus", "person"),
            ("Gaius Gracchus", "person"),
            ("Julius Caesar", "person"),
            ("Rubicon", "place"),
            ("Pompey", "person"),
            ("Pharsalus", "place"),
            ("Mark Antony", "person"),
            ("Cleopatra", "person"),
            ("Battle of Actium", "concept"),
        ],
        "relationships": [
            ("Lucius Junius Brutus", "overthrew", "Tarquin the Proud"),
            ("Cincinnatus", "served_as", "dictator"),
            ("Tiberius Gracchus", "brother_of", "Gaius Gracchus"),
            ("Julius Caesar", "crossed", "Rubicon"),
            ("Julius Caesar", "defeated", "Pompey"),
            ("Julius Caesar", "defeated_at", "Pharsalus"),
            ("Augustus", "defeated", "Mark Antony"),
            ("Augustus", "defeated", "Cleopatra"),
            ("Augustus", "won", "Battle of Actium"),
        ],
    },
    "french_revolution": {
        "entities": [
            ("French Revolution", "concept"),
            ("Bastille", "place"),
            ("Paris", "place"),
            ("Louis XVI", "person"),
            ("Marie Antoinette", "person"),
            ("Jean-Jacques Rousseau", "person"),
            ("Voltaire", "person"),
            ("Montesquieu", "person"),
            ("Estates-General", "org"),
            ("Versailles", "place"),
            ("National Assembly", "org"),
            ("Robespierre", "person"),
            ("Committee of Public Safety", "org"),
            ("Napoleon Bonaparte", "person"),
        ],
        "relationships": [
            ("French Revolution", "began_at", "Bastille"),
            ("Bastille", "located_in", "Paris"),
            ("Jean-Jacques Rousseau", "influenced", "French Revolution"),
            ("Voltaire", "influenced", "French Revolution"),
            ("Montesquieu", "influenced", "French Revolution"),
            ("Estates-General", "convened_at", "Versailles"),
            ("Robespierre", "led", "Committee of Public Safety"),
            ("Napoleon Bonaparte", "ended", "French Revolution"),
        ],
    },
    "apple_company_history": {
        "entities": [
            ("Apple", "org"),
            ("Steve Jobs", "person"),
            ("Steve Wozniak", "person"),
            ("Ronald Wayne", "person"),
            ("Los Altos", "place"),
            ("Apple I", "concept"),
            ("Apple II", "concept"),
            ("John Sculley", "person"),
            ("NeXT", "org"),
            ("Pixar", "org"),
            ("Toy Story", "concept"),
            ("Tim Cook", "person"),
            ("iMac", "concept"),
            ("iPod", "concept"),
            ("iPhone", "concept"),
            ("iPad", "concept"),
            ("Apple Vision Pro", "concept"),
        ],
        "relationships": [
            ("Apple", "founded_by", "Steve Jobs"),
            ("Apple", "founded_by", "Steve Wozniak"),
            ("Apple", "founded_by", "Ronald Wayne"),
            ("Apple", "founded_in", "Los Altos"),
            ("Steve Wozniak", "built", "Apple I"),
            ("Apple", "released", "Apple II"),
            ("Steve Jobs", "ousted_by", "John Sculley"),
            ("Steve Jobs", "founded", "NeXT"),
            ("Steve Jobs", "acquired", "Pixar"),
            ("Pixar", "released", "Toy Story"),
            ("Apple", "acquired", "NeXT"),
            ("Tim Cook", "succeeded", "Steve Jobs"),
            ("Apple", "released", "iMac"),
            ("Apple", "released", "iPod"),
            ("Apple", "released", "iPhone"),
            ("Apple", "released", "iPad"),
            ("Apple", "released", "Apple Vision Pro"),
        ],
    },
    "microsoft_history": {
        "entities": [
            ("Microsoft", "org"),
            ("Bill Gates", "person"),
            ("Paul Allen", "person"),
            ("Albuquerque", "place"),
            ("Seattle", "place"),
            ("Bellevue", "place"),
            ("Redmond", "place"),
            ("IBM", "org"),
            ("MS-DOS", "concept"),
            ("Seattle Computer Products", "org"),
            ("Windows 1.0", "concept"),
            ("Windows 95", "concept"),
            ("Steve Ballmer", "person"),
            ("Satya Nadella", "person"),
            ("Azure", "concept"),
            ("LinkedIn", "org"),
            ("GitHub", "org"),
            ("Activision Blizzard", "org"),
        ],
        "relationships": [
            ("Microsoft", "founded_by", "Bill Gates"),
            ("Microsoft", "founded_by", "Paul Allen"),
            ("Microsoft", "founded_in", "Albuquerque"),
            ("Microsoft", "moved_to", "Bellevue"),
            ("Microsoft", "moved_to", "Redmond"),
            ("IBM", "licensed", "MS-DOS"),
            ("Microsoft", "purchased_from", "Seattle Computer Products"),
            ("Microsoft", "released", "Windows 1.0"),
            ("Microsoft", "released", "Windows 95"),
            ("Steve Ballmer", "succeeded", "Bill Gates"),
            ("Satya Nadella", "succeeded", "Steve Ballmer"),
            ("Satya Nadella", "launched", "Azure"),
            ("Microsoft", "acquired", "LinkedIn"),
            ("Microsoft", "acquired", "GitHub"),
            ("Microsoft", "acquired", "Activision Blizzard"),
        ],
    },
    "amazon_company_history": {
        "entities": [
            ("Amazon", "org"),
            ("Jeff Bezos", "person"),
            ("Bellevue", "place"),
            ("Cadabra", "concept"),
            ("Amazon Prime", "concept"),
            ("Amazon Web Services", "org"),
            ("AWS", "org"),
            ("Andy Jassy", "person"),
            ("The Washington Post", "org"),
            ("Whole Foods Market", "org"),
            ("MGM Studios", "org"),
            ("iRobot", "org"),
        ],
        "relationships": [
            ("Amazon", "founded_by", "Jeff Bezos"),
            ("Amazon", "founded_in", "Bellevue"),
            ("Amazon", "originally_named", "Cadabra"),
            ("Amazon", "launched", "Amazon Prime"),
            ("Amazon", "launched", "Amazon Web Services"),
            ("Amazon Web Services", "also_known_as", "AWS"),
            ("Andy Jassy", "succeeded", "Jeff Bezos"),
            ("Jeff Bezos", "acquired", "The Washington Post"),
            ("Amazon", "acquired", "Whole Foods Market"),
            ("Amazon", "acquired", "MGM Studios"),
            ("Amazon", "acquired", "iRobot"),
        ],
    },
    "tesla_company_history": {
        "entities": [
            ("Tesla", "org"),
            ("Martin Eberhard", "person"),
            ("Marc Tarpenning", "person"),
            ("Elon Musk", "person"),
            ("Nikola Tesla", "person"),
            ("Tesla Roadster", "concept"),
            ("Model S", "concept"),
            ("Model 3", "concept"),
            ("Gigafactory", "concept"),
            ("Reno", "place"),
            ("Nevada", "place"),
            ("Shanghai", "place"),
            ("Berlin", "place"),
            ("Austin", "place"),
        ],
        "relationships": [
            ("Tesla", "founded_by", "Martin Eberhard"),
            ("Tesla", "founded_by", "Marc Tarpenning"),
            ("Elon Musk", "invested_in", "Tesla"),
            ("Tesla", "named_after", "Nikola Tesla"),
            ("Tesla", "released", "Tesla Roadster"),
            ("Tesla", "released", "Model S"),
            ("Tesla", "released", "Model 3"),
            ("Tesla", "opened", "Gigafactory"),
            ("Gigafactory", "located_in", "Reno"),
            ("Reno", "located_in", "Nevada"),
            ("Gigafactory", "located_in", "Shanghai"),
            ("Gigafactory", "located_in", "Berlin"),
            ("Gigafactory", "located_in", "Austin"),
        ],
    },
    "george_orwell": {
        "entities": [
            ("George Orwell", "person"),
            ("Eric Arthur Blair", "person"),
            ("Motihari", "place"),
            ("Bengal Presidency", "place"),
            ("British India", "place"),
            ("St Cyprian's School", "org"),
            ("Eastbourne", "place"),
            ("Eton College", "org"),
            ("Aldous Huxley", "person"),
            ("Indian Imperial Police", "org"),
            ("Burma", "place"),
            ("Burmese Days", "concept"),
            ("Animal Farm", "concept"),
            ("Secker and Warburg", "org"),
            ("London", "place"),
            ("Napoleon", "concept"),
            ("Joseph Stalin", "person"),
            ("Snowball", "concept"),
            ("Leon Trotsky", "person"),
            ("Old Major", "concept"),
            ("Karl Marx", "person"),
            ("Vladimir Lenin", "person"),
            ("Nineteen Eighty-Four", "concept"),
            ("Barnhill", "place"),
            ("Jura", "place"),
            ("University College Hospital", "org"),
        ],
        "relationships": [
            ("George Orwell", "pen_name_of", "Eric Arthur Blair"),
            ("Eric Arthur Blair", "born_in", "Motihari"),
            ("Motihari", "located_in", "Bengal Presidency"),
            ("Bengal Presidency", "part_of", "British India"),
            ("George Orwell", "educated_at", "St Cyprian's School"),
            ("St Cyprian's School", "located_in", "Eastbourne"),
            ("George Orwell", "educated_at", "Eton College"),
            ("Aldous Huxley", "taught_at", "Eton College"),
            ("George Orwell", "worked_at", "Indian Imperial Police"),
            ("Indian Imperial Police", "located_in", "Burma"),
            ("George Orwell", "wrote", "Burmese Days"),
            ("George Orwell", "wrote", "Animal Farm"),
            ("Animal Farm", "published_by", "Secker and Warburg"),
            ("Secker and Warburg", "located_in", "London"),
            ("Napoleon", "based_on", "Joseph Stalin"),
            ("Snowball", "based_on", "Leon Trotsky"),
            ("Old Major", "based_on", "Karl Marx"),
            ("Old Major", "based_on", "Vladimir Lenin"),
            ("George Orwell", "wrote", "Nineteen Eighty-Four"),
            ("Nineteen Eighty-Four", "written_at", "Barnhill"),
            ("Barnhill", "located_in", "Jura"),
            ("George Orwell", "died_at", "University College Hospital"),
        ],
    },
    "manhattan_project": {
        "entities": [
            ("Manhattan Project", "concept"),
            ("Albert Einstein", "person"),
            ("Leó Szilárd", "person"),
            ("Franklin D. Roosevelt", "person"),
            ("Einstein-Szilárd letter", "concept"),
            ("Alexander Sachs", "person"),
            ("Leslie Groves", "person"),
            ("US Army Corps of Engineers", "org"),
            ("J. Robert Oppenheimer", "person"),
            ("Los Alamos", "place"),
            ("New Mexico", "place"),
            ("Trinity test", "concept"),
            ("Alamogordo Bombing Range", "place"),
            ("Fat Man", "concept"),
            ("Little Boy", "concept"),
            ("Nagasaki", "place"),
            ("Hiroshima", "place"),
            ("Hanford Site", "place"),
            ("Washington", "place"),
            ("Glenn Seaborg", "person"),
            ("Clinton Engineer Works", "place"),
            ("Oak Ridge", "place"),
            ("Tennessee", "place"),
            ("Metallurgical Laboratory", "org"),
            ("University of Chicago", "org"),
            ("Enrico Fermi", "person"),
            ("Chicago Pile-1", "concept"),
        ],
        "relationships": [
            ("Albert Einstein", "co_wrote", "Einstein-Szilárd letter"),
            ("Leó Szilárd", "co_wrote", "Einstein-Szilárd letter"),
            ("Einstein-Szilárd letter", "addressed_to", "Franklin D. Roosevelt"),
            ("Alexander Sachs", "delivered", "Einstein-Szilárd letter"),
            ("Leslie Groves", "directed", "Manhattan Project"),
            ("Leslie Groves", "worked_at", "US Army Corps of Engineers"),
            ("J. Robert Oppenheimer", "led", "Los Alamos"),
            ("Los Alamos", "located_in", "New Mexico"),
            ("Manhattan Project", "conducted", "Trinity test"),
            ("Trinity test", "conducted_at", "Alamogordo Bombing Range"),
            ("Fat Man", "detonated_on", "Nagasaki"),
            ("Little Boy", "detonated_on", "Hiroshima"),
            ("Hanford Site", "located_in", "Washington"),
            ("Glenn Seaborg", "worked_at", "Hanford Site"),
            ("Clinton Engineer Works", "located_in", "Oak Ridge"),
            ("Oak Ridge", "located_in", "Tennessee"),
            ("Metallurgical Laboratory", "located_at", "University of Chicago"),
            ("Enrico Fermi", "led", "Metallurgical Laboratory"),
            ("Enrico Fermi", "built", "Chicago Pile-1"),
        ],
    },
    "berlin_conference_1884": {
        "entities": [
            ("Berlin Conference", "concept"),
            ("Berlin", "place"),
            ("Germany", "place"),
            ("Otto von Bismarck", "person"),
            ("Africa", "place"),
            ("Leopold II", "person"),
            ("Belgium", "place"),
            ("Congo Free State", "place"),
            ("Roger Casement", "person"),
            ("E.D. Morel", "person"),
            ("Casement Report", "concept"),
            ("Ethiopia", "place"),
            ("Menelik II", "person"),
            ("Liberia", "place"),
        ],
        "relationships": [
            ("Berlin Conference", "held_in", "Berlin"),
            ("Berlin", "located_in", "Germany"),
            ("Berlin Conference", "organised_by", "Otto von Bismarck"),
            ("Berlin Conference", "partitioned", "Africa"),
            ("Berlin Conference", "recognised_claim_of", "Leopold II"),
            ("Leopold II", "ruled", "Congo Free State"),
            ("Leopold II", "from", "Belgium"),
            ("Roger Casement", "exposed", "Congo Free State"),
            ("E.D. Morel", "exposed", "Congo Free State"),
            ("Roger Casement", "co_wrote", "Casement Report"),
            ("Menelik II", "ruled", "Ethiopia"),
            ("Ethiopia", "remained_independent_after", "Berlin Conference"),
            ("Liberia", "remained_independent_after", "Berlin Conference"),
        ],
    },
}


# 30 Q&A pairs. Each entry: (question, [expected_source_slugs], expected_answer_summary)
QA_PAIRS: list[tuple[str, list[str], str]] = [
    ("Who designed the Bombe?", ["alan_turing_life", "bletchley_park", "enigma_machine"], "Alan Turing designed the Bombe."),
    ("Where was Alan Turing born?", ["alan_turing_life"], "London."),
    ("Which university did Alan Turing attend?", ["alan_turing_life"], "University of Cambridge."),
    ("What machine did Tommy Flowers design?", ["bletchley_park"], "Colossus."),
    ("Who invented the Enigma machine?", ["enigma_machine"], "Arthur Scherbius."),
    ("What is the Church-Turing thesis?", ["turing_machine_concept"], "Any effectively calculable function can be computed by a Turing machine."),
    ("Who proved the Halting Problem undecidable?", ["turing_machine_concept"], "Alan Turing."),
    ("What was the ALPAC report?", ["ai_winter_1970s"], "A 1966 report by the US National Research Council concluding machine translation was not feasible."),
    ("Who invented the Perceptron?", ["ai_winter_1970s"], "Frank Rosenblatt."),
    ("What is AlexNet?", ["deep_learning_rise"], "A deep CNN that won the 2012 ImageNet competition, developed by Krizhevsky, Sutskever, and Hinton."),
    ("Who invented LSTM?", ["deep_learning_rise"], "Sepp Hochreiter and Jürgen Schmidhuber in 1997."),
    ("Who introduced the Transformer architecture?", ["transformer_architecture", "deep_learning_rise"], "Ashish Vaswani and colleagues at Google in 2017."),
    ("When was OpenAI founded?", ["openai_company"], "December 2015 in San Francisco."),
    ("Who invested USD 10 billion in OpenAI in 2023?", ["openai_company"], "Microsoft."),
    ("Who founded Anthropic?", ["anthropic_company"], "Dario Amodei and Daniela Amodei."),
    ("What is Constitutional AI?", ["anthropic_company"], "A training method where the model evaluates its own outputs against a written constitution of principles."),
    ("Who acquired DeepMind in 2014?", ["google_deepmind"], "Google, for USD 500 million."),
    ("Who won the 2024 Nobel Prize in Chemistry for AlphaFold?", ["google_deepmind"], "Demis Hassabis and John Jumper."),
    ("Who developed CRISPR-Cas9?", ["crispr_gene_editing"], "Jennifer Doudna and Emmanuelle Charpentier in 2012."),
    ("What was the first approved CRISPR therapy?", ["crispr_gene_editing"], "Casgevy for sickle cell disease, approved by the UK MHRA in November 2023."),
    ("Who crossed the Rubicon in 49 BCE?", ["roman_republic"], "Julius Caesar."),
    ("Where was the Battle of Actium fought?", ["roman_republic"], "It ended the Roman Republic; Augustus defeated Mark Antony and Cleopatra."),
    ("When did the French Revolution begin?", ["french_revolution"], "14 July 1789 with the storming of the Bastille in Paris."),
    ("Who led the Committee of Public Safety during the Reign of Terror?", ["french_revolution"], "Maximilien Robespierre."),
    ("Who co-founded Apple with Steve Jobs?", ["apple_company_history"], "Steve Wozniak and Ronald Wayne."),
    ("What was the first product Apple sold?", ["apple_company_history"], "The Apple I, hand-built by Steve Wozniak."),
    ("Who succeeded Bill Gates as Microsoft CEO?", ["microsoft_history"], "Steve Ballmer in January 2000."),
    ("What was Amazon's original name?", ["amazon_company_history"], "Cadabra (as in abracadabra)."),
    ("Who was Tesla named after?", ["tesla_company_history"], "Nikola Tesla, the Serbian-American inventor."),
    ("When did the Berlin Conference take place?", ["berlin_conference_1884"], "From 15 November 1884 to 26 February 1885 in Berlin, Germany."),
    ("Who organised the Berlin Conference?", ["berlin_conference_1884"], "Otto von Bismarck, Chancellor of Germany."),
    ("Who wrote Animal Farm?", ["george_orwell"], "George Orwell, published on 17 August 1945 by Secker and Warburg."),
    ("Where was Nineteen Eighty-Four written?", ["george_orwell"], "Barnhill, a remote farmhouse on the Scottish island of Jura."),
    ("Who led the Los Alamos laboratory during the Manhattan Project?", ["manhattan_project"], "J. Robert Oppenheimer."),
    ("What was the first self-sustaining nuclear chain reaction?", ["manhattan_project"], "Chicago Pile-1, built by Enrico Fermi at the University of Chicago on 2 December 1942."),
]

assert len(QA_PAIRS) >= 30, f"Expected at least 30 Q&A pairs, got {len(QA_PAIRS)}"
assert len(LABELS) == 20, f"Expected 20 labeled docs, got {len(LABELS)}"


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


def main() -> None:
    kinds = _assign_kinds()
    print(f"Generating {len(ARTICLES)} documents...")
    written = []
    for (slug, title, body), kind in zip(ARTICLES, kinds):
        path = DOCS_DIR / f"{slug}.{kind}"
        if kind == "md":
            _write_markdown(path, title, body)
        elif kind == "html":
            _write_html(path, title, body)
        elif kind == "pdf":
            _write_pdf(path, title, body)
        written.append((slug, kind, path.name))

    print(f"Wrote {len(written)} files to {DOCS_DIR}")

    # Labels
    with (LABELS_DIR / "labels.jsonl").open("w", encoding="utf-8") as f:
        for slug, data in LABELS.items():
            # Find the actual file name for this slug
            kind = next(k for s, k, _ in written if s == slug)
            fname = next(n for s, k, n in written if s == slug)
            entry = {
                "slug": slug,
                "file": fname,
                "kind": kind,
                "title": next(t for s, t, b in ARTICLES if s == slug),
                "entities": [{"name": n, "kind": k} for n, k in data["entities"]],
                "relationships": [
                    {"subject": s, "predicate": p, "object": o}
                    for s, p, o in data["relationships"]
                ],
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"Wrote {len(LABELS)} labels to {LABELS_DIR / 'labels.jsonl'}")

    # Q&A pairs
    slug_to_file = {s: n for s, k, n in written}
    with (QA_DIR / "qa_pairs.jsonl").open("w", encoding="utf-8") as f:
        for i, (q, sources, ans) in enumerate(QA_PAIRS, start=1):
            entry = {
                "id": i,
                "question": q,
                "expected_sources": [slug_to_file[s] for s in sources],
                "expected_answer_summary": ans,
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"Wrote {len(QA_PAIRS)} Q&A pairs to {QA_DIR / 'qa_pairs.jsonl'}")

    # Manifest
    manifest = {
        "n_documents": len(ARTICLES),
        "n_labeled": len(LABELS),
        "n_qa_pairs": len(QA_PAIRS),
        "kind_counts": {k: sum(1 for _, kk, _ in written if kk == k) for k in ["md", "html", "pdf"]},
        "documents": [
            {"slug": s, "kind": k, "file": n} for s, k, n in written
        ],
    }
    (ROOT / "data" / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Wrote manifest to {ROOT / 'data' / 'manifest.json'}")
    print(json.dumps(manifest["kind_counts"], indent=2))


if __name__ == "__main__":
    main()
