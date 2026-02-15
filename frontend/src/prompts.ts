export interface ToeflPrompt {
  id: string
  text: string
}

export const TOEFL_PROMPTS: ToeflPrompt[] = [
  { id: 'p01', text: "Do you agree or disagree that modern technology makes people's lives easier?" },
  { id: 'p02', text: 'Do the advantages of studying abroad outweigh the disadvantages?' },
  { id: 'p03', text: "What are the main causes of stress in modern society, and what effects does stress have on people's lives?" },
  { id: 'p04', text: 'Some people prefer to work in a large company, while others prefer to work in a small company. Which do you prefer and why?' },
  { id: 'p05', text: 'Do you agree or disagree that people today have less free time than people did in the past?' },
  { id: 'p06', text: 'Which is more important for a successful life: intelligence or hard work?' },
  { id: 'p07', text: 'Do you agree or disagree that students should be required to take physical education classes at university?' },
  { id: 'p08', text: 'Has social media had a more positive or more negative effect on communication between people?' },
  { id: 'p09', text: 'Do you think it is better to live alone or with roommates? Explain your opinion.' },
  { id: 'p10', text: 'Do you agree or disagree that governments should spend more money on public transportation rather than building new roads?' },
]
